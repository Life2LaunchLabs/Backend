"""
Admin quest management views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Prefetch
from django.shortcuts import get_object_or_404
from ..models import QuestTemplate, QuestItemDefinition, QuestTemplateItem
from ..serializers import (
    QuestTemplateSerializer,
    QuestTemplateDetailSerializer,
    QuestTemplateCreateSerializer,
    QuestItemDefinitionSerializer,
    QuestItemDefinitionCreateSerializer,
    QuestTemplateItemSerializer,
    QuestTemplateItemCreateSerializer,
)
from ..services.quest_ordering_service import QuestOrderingService


class QuestTemplateViewSet(viewsets.ModelViewSet):
    """Admin management of quest templates."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return QuestTemplateCreateSerializer
        elif self.action == 'retrieve':
            return QuestTemplateDetailSerializer
        return QuestTemplateSerializer

    def get_queryset(self):
        """Return quests for user's admin organizations."""
        user = self.request.user
        admin_org_ids = user.admin_organizations.values_list('id', flat=True)

        queryset = QuestTemplate.objects.filter(
            organization_id__in=admin_org_ids
        ).select_related('organization', 'created_by')

        # Add prefetch for detail view
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'template_items',
                    queryset=QuestTemplateItem.objects.select_related(
                        'item_definition', 'item_definition__activity'
                    ).prefetch_related('prerequisites').order_by('order')
                )
            )
        else:
            # For list view, just prefetch template_items for counts
            queryset = queryset.prefetch_related('template_items__item_definition')

        return queryset

    @action(detail=True, methods=['post'])
    def reorder_items(self, request, pk=None):
        """
        Reorder quest items atomically.
        Expected payload: {"item_orders": [{"id": "uuid", "order": 0}, ...]}
        """
        quest_template = self.get_object()
        item_orders = request.data.get('item_orders', [])

        if not item_orders:
            return Response(
                {"error": "item_orders required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            QuestOrderingService.reorder_items(quest_template.id, item_orders)
            return Response({"status": "reordered"})
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add an item to this quest."""
        quest_template = self.get_object()

        # Create a copy of request data and add quest_template
        data = request.data.copy()
        data['quest_template'] = quest_template.id

        serializer = QuestTemplateItemCreateSerializer(data=data)
        if serializer.is_valid():
            template_item = serializer.save()
            return Response(
                QuestTemplateItemSerializer(template_item).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_activity(self, request, pk=None):
        """
        Create a new blank activity tied to this quest.
        Returns the activity ID for navigation.
        """
        from django.db import transaction
        from ..models import Activity, ActivityVersion, QuestItemDefinition, Page, Block
        import uuid

        quest_template = self.get_object()
        user = request.user

        # Validate user has access to the organization
        if not user.admin_organizations.filter(id=quest_template.organization_id).exists():
            return Response(
                {"error": "Not an admin of this organization"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():
                # Generate unique slug for the activity
                activity_slug = f"activity-{uuid.uuid4().hex[:8]}"

                # Create blank activity
                activity = Activity.objects.create(
                    slug=activity_slug,
                    organization=quest_template.organization,
                    status='draft',
                    author_meta={'created_by': user.username, 'created_from_quest': str(quest_template.id)}
                )

                # Create initial blank version
                activity_version = ActivityVersion.objects.create(
                    activity=activity,
                    version=1,
                    title='New Activity',
                    description='',
                    is_published=True,
                    meta={'created_from_quest': str(quest_template.id)}
                )

                # Create a single blank page
                page = Page.objects.create(
                    activity_version=activity_version,
                    index=0,
                    title='Page 1',
                    meta={}
                )

                # Add a blank text block
                Block.objects.create(
                    page=page,
                    index=0,
                    block_type='text',
                    config={
                        'style': 'body',
                        'text': 'Start editing your activity here...',
                        'align': 'left'
                    }
                )

                # Create item definition for this activity
                item_definition = QuestItemDefinition.objects.create(
                    item_type='activity',
                    title=activity_version.title,
                    description=activity_version.description,
                    estimated_duration_days=1,
                    activity=activity,
                    organization=quest_template.organization
                )

                # Calculate next order position
                last_item = quest_template.template_items.order_by('-order').first()
                next_order = (last_item.order + 1) if last_item else 0

                # Add to quest template
                from ..models import QuestTemplateItem
                QuestTemplateItem.objects.create(
                    quest_template=quest_template,
                    item_definition=item_definition,
                    order=next_order
                )

                return Response({
                    'activity_id': str(activity.id),
                    'message': 'Activity created and added to quest'
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to create activity: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='remove_item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        """Remove an item from this quest."""
        quest_template = self.get_object()
        template_item = get_object_or_404(
            QuestTemplateItem,
            id=item_id,
            quest_template=quest_template
        )

        # Check if other items depend on this as prerequisite
        dependents = QuestTemplateItem.objects.filter(
            prerequisites=template_item
        ).select_related('item_definition')

        if dependents.exists():
            dependent_titles = [item.item_definition.title for item in dependents]
            return Response(
                {
                    "error": "Cannot remove item with prerequisites",
                    "dependents": dependent_titles
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        template_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a quest template."""
        quest_template = self.get_object()

        # Validate quest has items
        if not quest_template.template_items.exists():
            return Response(
                {"error": "Cannot publish quest with no items"},
                status=status.HTTP_400_BAD_REQUEST
            )

        quest_template.status = 'published'
        quest_template.save()

        serializer = self.get_serializer(quest_template)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a quest template."""
        quest_template = self.get_object()
        quest_template.status = 'draft'
        quest_template.save()

        serializer = self.get_serializer(quest_template)
        return Response(serializer.data)


class QuestItemDefinitionViewSet(viewsets.ModelViewSet):
    """Admin management of quest item definitions (the library)."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return QuestItemDefinitionCreateSerializer
        return QuestItemDefinitionSerializer

    def get_queryset(self):
        """Return item definitions for user's admin organizations."""
        user = self.request.user
        admin_org_ids = user.admin_organizations.values_list('id', flat=True)

        queryset = QuestItemDefinition.objects.filter(
            organization_id__in=admin_org_ids
        ).select_related('organization', 'activity')

        # Filter by item_type if specified
        item_type = self.request.query_params.get('item_type')
        if item_type:
            queryset = queryset.filter(item_type=item_type)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def available_for_quest(self, request):
        """
        Get item definitions not already in a specific quest.
        Query param: quest_template_id
        """
        quest_template_id = request.query_params.get('quest_template_id')
        if not quest_template_id:
            return Response(
                {"error": "quest_template_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get IDs of items already in this quest
        used_item_ids = QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id
        ).values_list('item_definition_id', flat=True)

        # Get all items not in this quest
        queryset = self.get_queryset().exclude(id__in=used_item_ids)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class QuestTemplateItemViewSet(viewsets.ModelViewSet):
    """Manage individual quest template items (for editing prerequisites, duration, etc)."""
    permission_classes = [IsAuthenticated]
    serializer_class = QuestTemplateItemSerializer

    def get_queryset(self):
        """Return template items for user's admin organizations."""
        user = self.request.user
        admin_org_ids = user.admin_organizations.values_list('id', flat=True)

        return QuestTemplateItem.objects.filter(
            quest_template__organization_id__in=admin_org_ids
        ).select_related(
            'quest_template',
            'item_definition',
            'item_definition__activity'
        ).prefetch_related('prerequisites')

    def update(self, request, *args, **kwargs):
        """Update template item (e.g., prerequisites, override duration)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Don't allow changing quest_template or item_definition
        data = request.data.copy()
        data.pop('quest_template', None)
        data.pop('item_definition', None)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)