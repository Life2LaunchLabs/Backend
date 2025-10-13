"""
Admin media management views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from ..models import MediaAsset
from ..services import MediaService
from ..serializers import MediaAssetSerializer


class MediaAssetViewSet(viewsets.ModelViewSet):
    """
    Admin management of media assets.
    Supports uploading images for use in activities.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MediaAssetSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """Return all media assets."""
        return MediaAsset.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """
        Upload a new media asset.

        Expects:
        - file: The image/media file to upload
        - title: Optional title for the media
        - description: Optional description
        - alt_text: Optional alt text for accessibility
        - organization_id: Optional organization UUID
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get optional metadata from request
        title = request.data.get('title', file.name)
        description = request.data.get('description', '')
        alt_text = request.data.get('alt_text', description)
        organization_id = request.data.get('organization_id')

        # If no organization_id provided, try to get user's default organization
        if not organization_id and hasattr(request.user, 'admin_organizations'):
            default_org = request.user.admin_organizations.first()
            if default_org:
                organization_id = str(default_org.id)

        try:
            # Read file content
            file_content = file.read()

            # Create media asset using service
            meta = {
                'title': title,
                'description': description,
                'alt_text': alt_text,
            }

            media_asset = MediaService.create_media_asset(
                file_content=file_content,
                filename=file.name,
                meta=meta,
                organization_id=organization_id
            )

            # Serialize and return
            serializer = self.get_serializer(media_asset)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to upload media: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete a media asset."""
        instance = self.get_object()

        try:
            success = MediaService.delete_media_asset(instance)
            if success:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"error": "Failed to delete media asset"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete media: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def activity_media(self, request):
        """
        Get all media assets suitable for activities.
        Filters to only show image files in the activities directory.
        """
        queryset = MediaAsset.objects.filter(
            storage_key__startswith='activities/',
            mime_type__startswith='image/'
        ).order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
