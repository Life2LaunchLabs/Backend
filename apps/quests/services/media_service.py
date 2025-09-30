import os
import hashlib
import mimetypes
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string
from ..models import MediaAsset


class MediaService:
    """Service for handling media assets with secure storage and URL generation."""

    @staticmethod
    def create_media_asset(file_content: bytes, filename: str, meta: Optional[Dict] = None) -> MediaAsset:
        """
        Create a MediaAsset from file content.

        Args:
            file_content: The binary content of the file
            filename: Original filename
            meta: Optional metadata dictionary

        Returns:
            MediaAsset instance
        """
        # Generate unique storage key
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        file_ext = os.path.splitext(filename)[1].lower()
        storage_key = f"media/{get_random_string(8)}/{file_hash}{file_ext}"

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Calculate checksum
        checksum = hashlib.md5(file_content).hexdigest()

        # Store file
        file_obj = ContentFile(file_content, name=storage_key)
        stored_path = default_storage.save(storage_key, file_obj)

        # Create MediaAsset
        media_asset = MediaAsset.objects.create(
            storage_key=stored_path,
            mime_type=mime_type,
            checksum=checksum,
            meta=meta or {}
        )

        # Extract metadata based on file type
        MediaService._extract_metadata(media_asset, file_content)
        media_asset.save()

        return media_asset

    @staticmethod
    def _extract_metadata(media_asset: MediaAsset, file_content: bytes) -> None:
        """Extract metadata from file content based on MIME type."""
        try:
            if media_asset.mime_type.startswith('image/'):
                # For images, try to get dimensions
                try:
                    from PIL import Image
                    import io
                    with Image.open(io.BytesIO(file_content)) as img:
                        media_asset.width, media_asset.height = img.size
                except ImportError:
                    pass  # PIL not available
                except Exception:
                    pass  # Failed to process image

            elif media_asset.mime_type.startswith('video/'):
                # For videos, could extract duration/dimensions with ffmpeg
                # For now, just placeholder
                pass

            elif media_asset.mime_type.startswith('audio/'):
                # For audio, could extract duration
                # For now, just placeholder
                pass
        except Exception:
            # Don't fail if metadata extraction fails
            pass

    @staticmethod
    def get_media_url(media_asset: MediaAsset, signed: bool = False) -> str:
        """
        Get URL for a media asset.

        Args:
            media_asset: MediaAsset instance
            signed: Whether to generate a signed URL (for private media)

        Returns:
            URL string
        """
        if signed:
            # TODO: Implement signed URL generation for private media
            # For now, return regular URL
            pass

        # Use Django's storage URL method
        url = default_storage.url(media_asset.storage_key)

        # For local development, ensure we return a fully qualified URL
        if settings.DEBUG and url.startswith('/'):
            # Get the base URL from settings or construct it
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            url = base_url + url

        return url

    @staticmethod
    def delete_media_asset(media_asset: MediaAsset) -> bool:
        """
        Delete a media asset and its file.

        Args:
            media_asset: MediaAsset instance to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the file from storage
            if default_storage.exists(media_asset.storage_key):
                default_storage.delete(media_asset.storage_key)

            # Delete the database record
            media_asset.delete()
            return True
        except Exception:
            return False

    @staticmethod
    def bulk_resolve_media(media_ids: list) -> Dict[str, Dict[str, Any]]:
        """
        Resolve multiple media IDs to their metadata and URLs.

        Args:
            media_ids: List of MediaAsset UUID strings

        Returns:
            Dictionary mapping media_id to metadata dict
        """
        media_assets = MediaAsset.objects.filter(id__in=media_ids)

        result = {}
        for asset in media_assets:
            result[str(asset.id)] = {
                'media_id': str(asset.id),
                'url': MediaService.get_media_url(asset),
                'mime_type': asset.mime_type,
                'width': asset.width,
                'height': asset.height,
                'duration_ms': asset.duration_ms,
                'meta': asset.meta
            }

        return result
