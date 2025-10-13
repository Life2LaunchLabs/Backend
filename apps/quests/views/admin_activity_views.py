"""
Admin activity management views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from ..models import Activity, ActivityVersion, Page, Block
from ..serializers import (
    ActivitySerializer,
    ActivityDetailSerializer,
    ActivityVersionSerializer,
)


class ActivityViewSet(viewsets.ModelViewSet):
    """Admin management of activities."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityDetailSerializer
        return ActivitySerializer

    def get_queryset(self):
        """Return activities for user's admin organizations."""
        user = self.request.user
        admin_org_ids = user.admin_organizations.values_list('id', flat=True)

        queryset = Activity.objects.filter(
            organization_id__in=admin_org_ids
        ).select_related('organization')

        # For detail view, prefetch versions with pages and blocks
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'versions',
                    queryset=ActivityVersion.objects.filter(
                        is_published=True
                    ).prefetch_related(
                        Prefetch(
                            'pages',
                            queryset=Page.objects.prefetch_related('blocks').order_by('index')
                        )
                    ).order_by('-version')
                )
            )

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Create a new activity with initial version."""
        # Validate organization access
        user = request.user
        organization_id = request.data.get('organization')

        if not user.admin_organizations.filter(id=organization_id).exists():
            return Response(
                {"error": "Not an admin of this organization"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create activity
        activity = Activity.objects.create(
            slug=request.data.get('slug'),
            organization_id=organization_id,
            status='draft',
            author_meta=request.data.get('author_meta', {})
        )

        # Create initial version
        ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title=request.data.get('title', 'Untitled Activity'),
            description=request.data.get('description', ''),
            meta=request.data.get('meta', {}),
            is_published=False
        )

        serializer = self.get_serializer(activity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish the latest activity version."""
        activity = self.get_object()

        # Get latest version
        latest_version = activity.versions.order_by('-version').first()
        if not latest_version:
            return Response(
                {"error": "No versions to publish"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate version has at least one page
        if not latest_version.pages.exists():
            return Response(
                {"error": "Cannot publish activity with no pages"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Unpublish all other versions
        activity.versions.update(is_published=False)

        # Publish latest version
        latest_version.is_published = True
        latest_version.save()

        # Update activity status
        activity.status = 'published'
        activity.save()

        serializer = self.get_serializer(activity)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish activity."""
        activity = self.get_object()

        # Unpublish all versions
        activity.versions.update(is_published=False)

        # Update activity status
        activity.status = 'draft'
        activity.save()

        serializer = self.get_serializer(activity)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """Create a new version of this activity."""
        activity = self.get_object()

        # Get latest version number
        latest_version = activity.versions.order_by('-version').first()
        new_version_number = (latest_version.version + 1) if latest_version else 1

        # Create new version
        new_version = ActivityVersion.objects.create(
            activity=activity,
            version=new_version_number,
            title=request.data.get('title', latest_version.title if latest_version else 'Untitled'),
            description=request.data.get('description', latest_version.description if latest_version else ''),
            meta=request.data.get('meta', latest_version.meta if latest_version else {}),
            is_published=False
        )

        serializer = ActivityVersionSerializer(new_version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put'])
    def save_edits(self, request, pk=None):
        """Comprehensive save endpoint that handles activity, pages, and blocks in one transaction."""
        from django.db import transaction
        activity = self.get_object()

        try:
            with transaction.atomic():
                # Extract data from request
                activity_data = request.data.get('activity', {})
                activity_version_data = request.data.get('activity_version', {})
                pages_data = request.data.get('pages', [])

                # Update activity if provided (only non-version-specific fields)
                if activity_data:
                    activity.status = activity_data.get('status', activity.status)
                    activity.author_meta = activity_data.get('author_meta', activity.author_meta)
                    activity.save()

                # Create new version
                latest_version = activity.versions.filter(is_published=True).order_by('-version').first()
                next_version_number = (latest_version.version + 1) if latest_version else 1

                # Get title and description from activity_version_data, fallback to latest version
                title = activity_version_data.get('title', latest_version.title if latest_version else 'Untitled Activity')
                description = activity_version_data.get('description', latest_version.description if latest_version else '')

                new_version = ActivityVersion.objects.create(
                    activity=activity,
                    version=next_version_number,
                    title=title,
                    description=description,
                    meta=activity_version_data.get('meta', {}),
                    is_published=True
                )

                # Create pages and blocks
                for page_data in pages_data:
                    page = Page.objects.create(
                        activity_version=new_version,
                        index=page_data.get('index', 0),
                        title=page_data.get('title', ''),
                        meta=page_data.get('meta', {})
                    )

                    # Create blocks for this page
                    blocks_data = page_data.get('blocks', [])
                    for i, block_data in enumerate(blocks_data):
                        Block.objects.create(
                            page=page,
                            index=i,
                            block_type=block_data.get('block_type', block_data.get('type', 'text')),
                            config=block_data.get('config', {})
                        )

                return Response({
                    'message': 'Activity saved successfully',
                    'activity': {
                        'id': str(activity.id),
                        'slug': activity.slug,
                        'title': activity.title,
                        'description': activity.description
                    },
                    'new_version': {
                        'id': str(new_version.id),
                        'version': new_version.version,
                        'title': new_version.title
                    }
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'Failed to save activity: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class ActivityVersionViewSet(viewsets.ModelViewSet):
    """Manage activity versions (pages and blocks)."""
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityVersionSerializer

    def get_queryset(self):
        """Return activity versions for user's admin organizations."""
        user = self.request.user
        admin_org_ids = user.admin_organizations.values_list('id', flat=True)

        return ActivityVersion.objects.filter(
            activity__organization_id__in=admin_org_ids
        ).select_related('activity').prefetch_related(
            Prefetch(
                'pages',
                queryset=Page.objects.prefetch_related('blocks').order_by('index')
            )
        ).order_by('-version')

    def update(self, request, *args, **kwargs):
        """Update version metadata (title, description, meta)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Don't allow updating if published
        if instance.is_published:
            return Response(
                {"error": "Cannot edit published version. Create a new version instead."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_page(self, request, pk=None):
        """Add a new page to this version."""
        version = self.get_object()

        if version.is_published:
            return Response(
                {"error": "Cannot edit published version"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get next index
        last_page = version.pages.order_by('-index').first()
        next_index = (last_page.index + 1) if last_page else 0

        # Create page
        page = Page.objects.create(
            activity_version=version,
            index=request.data.get('index', next_index),
            title=request.data.get('title', 'New Page'),
            meta=request.data.get('meta', {})
        )

        from ..serializers import PageSerializer
        serializer = PageSerializer(page)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reorder_pages(self, request, pk=None):
        """Reorder pages in this version."""
        version = self.get_object()

        if version.is_published:
            return Response(
                {"error": "Cannot edit published version"},
                status=status.HTTP_400_BAD_REQUEST
            )

        page_orders = request.data.get('page_orders', [])
        if not page_orders:
            return Response(
                {"error": "page_orders required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update page indices
        for item in page_orders:
            Page.objects.filter(
                id=item['id'],
                activity_version=version
            ).update(index=item['index'])

        serializer = self.get_serializer(version)
        return Response(serializer.data)