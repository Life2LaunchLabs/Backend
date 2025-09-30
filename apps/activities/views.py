from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import (
    MediaAsset, QuestionPackage, Activity, ActivityVersion,
    Page, Block, QuestDefinition, QuestInstance, Attempt,
    PageProgress, Response, ActivitySubmission, SubmissionResponse
)
from .serializers import (
    MediaAssetSerializer, MediaAssetCreateSerializer, MediaResolver,
    QuestionPackageSerializer, ActivitySerializer, ActivityDetailSerializer,
    ActivityVersionSerializer, PageSerializer, BlockSerializer,
    QuestDefinitionSerializer, QuestInstanceSerializer,
    AttemptSerializer, AttemptCreateSerializer, PageProgressSerializer,
    ResponseSerializer, ResponseCreateSerializer, BatchResponseCreateSerializer,
    ActivitySubmissionSerializer, ActivitySubmissionDetailSerializer, SubmissionResponseSerializer
)
from .services import MediaService


class MediaAssetViewSet(viewsets.ModelViewSet):
    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return MediaAssetCreateSerializer
        return MediaAssetSerializer

    @action(detail=False, methods=['post'])
    def resolve_bulk(self, request):
        """Resolve multiple media IDs to their metadata."""
        media_ids = request.data.get('media_ids', [])
        if not media_ids:
            return DRFResponse({'error': 'media_ids required'}, status=status.HTTP_400_BAD_REQUEST)

        media_data = MediaService.bulk_resolve_media(media_ids)
        serializer = MediaResolver(data=list(media_data.values()), many=True)
        serializer.is_valid(raise_exception=True)
        return DRFResponse(serializer.data)


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.filter(status__in=['published', 'draft'])
    serializer_class = ActivitySerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Allow public access to list and retrieve published activities.
        Require authentication for other operations.
        """
        if self.action in ['list', 'retrieve']:
            # For map/public viewing of published activities
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        if self.action in ['list', 'retrieve']:
            # Public access: only show published activities
            return Activity.objects.filter(status='published')
        # Authenticated access: show all activities user has access to
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityDetailSerializer
        return ActivitySerializer

    def get_object(self):
        """Get activity with prefetched latest published version."""
        # Use explicit lookup with id parameter
        activity = get_object_or_404(self.get_queryset(), id=self.kwargs['id'])

        # Prefetch the latest published version for detailed view
        if self.action == 'retrieve':
            latest_version = activity.versions.filter(is_published=True).order_by('-version').first()
            if latest_version:
                # Prefetch pages and blocks for efficiency
                latest_version = ActivityVersion.objects.select_related().prefetch_related(
                    'pages__blocks'
                ).get(id=latest_version.id)
                activity._prefetched_activity_version = latest_version

        return activity

    @action(detail=True, methods=['get'])
    def latest(self, request, id=None):
        """Get the latest published version of an activity."""
        activity = self.get_object()
        latest_version = activity.versions.filter(is_published=True).order_by('-version').first()

        if not latest_version:
            return DRFResponse({'error': 'No published version found'},
                             status=status.HTTP_404_NOT_FOUND)

        # Prefetch related data for efficiency
        latest_version = ActivityVersion.objects.select_related().prefetch_related(
            'pages__blocks'
        ).get(id=latest_version.id)

        serializer = ActivityVersionSerializer(latest_version)
        return DRFResponse(serializer.data)

    @action(detail=True, methods=['get'])
    def page(self, request, id=None):
        """Get a specific page of an activity with resolved media."""
        activity = self.get_object()
        page_index = request.query_params.get('index', 0)

        try:
            page_index = int(page_index)
        except (ValueError, TypeError):
            return DRFResponse({'error': 'Invalid page index'},
                             status=status.HTTP_400_BAD_REQUEST)

        latest_version = activity.versions.filter(is_published=True).order_by('-version').first()
        if not latest_version:
            return DRFResponse({'error': 'No published version found'},
                             status=status.HTTP_404_NOT_FOUND)

        try:
            page = latest_version.pages.get(index=page_index)
        except Page.DoesNotExist:
            return DRFResponse({'error': 'Page not found'},
                             status=status.HTTP_404_NOT_FOUND)

        # Get all blocks for this page
        blocks = page.blocks.all().order_by('index')

        # Extract and resolve media IDs
        media_ids = set()
        for block in blocks:
            if block.block_type == 'media' and 'media_id' in block.config:
                media_ids.add(block.config['media_id'])
            elif block.block_type == 'question' and 'config' in block.config:
                question_config = block.config.get('config', {})
                if 'options' in question_config:
                    for option in question_config['options']:
                        if 'media_id' in option:
                            media_ids.add(option['media_id'])

        # Resolve media
        media_data = []
        if media_ids:
            media_dict = MediaService.bulk_resolve_media(list(media_ids))
            media_data = list(media_dict.values())

        return DRFResponse({
            'activity_version': {
                'id': str(latest_version.id),
                'version': latest_version.version,
                'title': latest_version.title,
                'meta': latest_version.meta
            },
            'page': {
                'id': str(page.id),
                'index': page.index,
                'title': page.title,
                'meta': page.meta
            },
            'blocks': [
                {
                    'id': str(block.id),
                    'type': block.block_type,
                    'config': block.config
                }
                for block in blocks
            ],
            'media': media_data
        })

    @action(detail=True, methods=['put'])
    def save_edits(self, request, id=None):
        """Comprehensive save endpoint that handles activity, pages, and blocks in one transaction."""
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
                            block_type=block_data.get('type', 'text'),
                            config=block_data.get('config', {})
                        )

                return DRFResponse({
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
            return DRFResponse({
                'error': f'Failed to save activity: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class PageViewSet(viewsets.ModelViewSet):
    """CRUD operations for individual pages."""
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Page.objects.all()


class BlockViewSet(viewsets.ModelViewSet):
    """CRUD operations for individual blocks."""
    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Block.objects.all()


class ActivityVersionViewSet(viewsets.ModelViewSet):
    """CRUD operations for activity versions."""
    serializer_class = ActivityVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivityVersion.objects.all()


class QuestionPackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuestionPackage.objects.all()
    serializer_class = QuestionPackageSerializer
    permission_classes = [IsAuthenticated]


class QuestDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuestDefinition.objects.all()
    serializer_class = QuestDefinitionSerializer
    lookup_field = 'slug'
    permission_classes = [IsAuthenticated]


class QuestInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = QuestInstanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QuestInstance.objects.filter(user=self.request.user)


class AttemptViewSet(viewsets.ModelViewSet):
    serializer_class = AttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Attempt.objects.filter(user=self.request.user).select_related(
            'activity_version', 'activity_version__activity', 'quest_instance'
        ).prefetch_related('responses')

        # Filter by activity if provided
        activity_id = self.request.query_params.get('activity_id')
        if activity_id:
            queryset = queryset.filter(activity_version__activity_id=activity_id)

        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Order by most recent first
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return AttemptCreateSerializer
        return AttemptSerializer

    def create(self, request, *args, **kwargs):
        """Create a new attempt and return it with AttemptSerializer."""
        create_serializer = AttemptCreateSerializer(data=request.data, context={'request': request})
        create_serializer.is_valid(raise_exception=True)
        attempt = create_serializer.save()

        # Serialize the created attempt with the proper serializer
        response_serializer = AttemptSerializer(attempt)
        return DRFResponse(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an attempt by converting to permanent submission and cleaning up."""
        attempt = self.get_object()
        if attempt.status == 'completed':
            return DRFResponse({'error': 'Attempt already completed'},
                             status=status.HTTP_400_BAD_REQUEST)

        # Create permanent submission record
        from django.utils import timezone
        from datetime import timedelta

        completed_at = timezone.now()
        time_taken = completed_at - attempt.started_at

        submission = ActivitySubmission.objects.create(
            user=attempt.user,
            activity_version=attempt.activity_version,
            quest_instance=attempt.quest_instance,
            started_at=attempt.started_at,
            time_taken=time_taken,
            meta=attempt.meta
        )

        # Copy all responses to submission responses
        for response in attempt.responses.all():
            SubmissionResponse.objects.create(
                submission=submission,
                question_id=response.question_id,
                question_type=response.question_type,
                page=response.page,
                value=response.value,
                valid=response.valid,
                meta=response.meta
            )

        # Clean up the temporary attempt
        attempt.delete()

        # Return submission data
        serializer = ActivitySubmissionSerializer(submission)
        return DRFResponse(serializer.data)

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        """Mark an attempt as abandoned."""
        attempt = self.get_object()
        if attempt.status == 'completed':
            return DRFResponse({'error': 'Cannot abandon completed attempt'},
                             status=status.HTTP_400_BAD_REQUEST)

        attempt.status = 'abandoned'
        attempt.save()

        serializer = self.get_serializer(attempt)
        return DRFResponse(serializer.data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get progress information for an attempt."""
        attempt = self.get_object()
        progress = PageProgress.objects.filter(attempt=attempt).select_related('page')
        serializer = PageProgressSerializer(progress, many=True)
        return DRFResponse(serializer.data)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update page progress for an attempt."""
        attempt = self.get_object()
        page_id = request.data.get('page_id')
        reached = request.data.get('reached', True)
        data = request.data.get('data', {})

        if not page_id:
            return DRFResponse({'error': 'page_id required'},
                             status=status.HTTP_400_BAD_REQUEST)

        try:
            page = Page.objects.get(id=page_id)
        except Page.DoesNotExist:
            return DRFResponse({'error': 'Page not found'},
                             status=status.HTTP_404_NOT_FOUND)

        progress, created = PageProgress.objects.update_or_create(
            attempt=attempt,
            page=page,
            defaults={
                'reached': reached,
                'data': data
            }
        )

        serializer = PageProgressSerializer(progress)
        return DRFResponse(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_response(self, request, pk=None):
        """Submit a single response for an attempt."""
        attempt = self.get_object()
        serializer = ResponseCreateSerializer(data=request.data, context={'attempt': attempt})
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return DRFResponse(ResponseSerializer(response).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit_responses(self, request, pk=None):
        """Submit multiple responses for an attempt."""
        attempt = self.get_object()
        serializer = BatchResponseCreateSerializer(data=request.data, context={'attempt': attempt})
        serializer.is_valid(raise_exception=True)
        responses = serializer.save()

        return DRFResponse(ResponseSerializer(responses, many=True).data,
                         status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        """Get all responses for an attempt."""
        attempt = self.get_object()
        responses = attempt.responses.all().order_by('created_at')
        serializer = ResponseSerializer(responses, many=True)
        return DRFResponse(serializer.data)


class HealthCheckView(APIView):
    """Health check endpoint for activities API."""
    permission_classes = []

    def get(self, request):
        return DRFResponse({
            'status': 'healthy',
            'service': 'activities',
            'timestamp': timezone.now().isoformat()
        })


class DemoDataView(APIView):
    """Create demo data for testing."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services import ActivityService

        try:
            activity = ActivityService.create_demo_activity()
            serializer = ActivitySerializer(activity)
            return DRFResponse({
                'message': 'Demo activity created successfully',
                'activity': serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return DRFResponse({
                'error': f'Failed to create demo activity: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# New ViewSets for improved session/submission architecture

class ActivitySubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for completed activity submissions.
    This is what the results page should use - only completed activities.
    """
    serializer_class = ActivitySubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ActivitySubmission.objects.filter(user=self.request.user).select_related(
            'activity_version', 'activity_version__activity', 'quest_instance'
        ).prefetch_related('responses')

        # Filter by activity if provided
        activity_id = self.request.query_params.get('activity_id')
        if activity_id:
            queryset = queryset.filter(activity_version__activity_id=activity_id)

        return queryset.order_by('-completed_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivitySubmissionDetailSerializer
        return ActivitySubmissionSerializer

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        """Get all responses for a submission."""
        submission = self.get_object()
        responses = submission.responses.all().order_by('created_at')
        serializer = SubmissionResponseSerializer(responses, many=True)
        return DRFResponse(serializer.data)


class ActivityResultsViewSet(viewsets.GenericViewSet):
    """
    Specialized ViewSet for activity results functionality.
    Provides convenient endpoints for the results page.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='activity/(?P<activity_id>[^/.]+)')
    def activity_results(self, request, activity_id=None):
        """Get all completed submissions for a specific activity."""
        submissions = ActivitySubmission.objects.filter(
            user=request.user,
            activity_version__activity_id=activity_id
        ).select_related('activity_version', 'quest_instance').order_by('-completed_at')

        serializer = ActivitySubmissionSerializer(submissions, many=True)
        return DRFResponse(serializer.data)

    @action(detail=False, methods=['get'], url_path='has-completed/(?P<activity_id>[^/.]+)')
    def has_completed(self, request, activity_id=None):
        """Check if user has completed an activity."""
        has_completed = ActivitySubmission.objects.filter(
            user=request.user,
            activity_version__activity_id=activity_id
        ).exists()

        return DRFResponse({'has_completed': has_completed})