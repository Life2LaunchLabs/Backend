"""
Activity serializers (moved from apps.activities).
"""
from rest_framework import serializers
from ..models import (
    MediaAsset, Activity, ActivityVersion, Page, Block
)


class MediaAssetSerializer(serializers.ModelSerializer):
    """Serializer for media assets."""
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = ['id', 'storage_key', 'mime_type', 'width', 'height',
                 'duration_ms', 'meta', 'url', 'created_at']
        read_only_fields = ['id', 'storage_key', 'created_at']

    def get_url(self, obj):
        """Get media URL - placeholder for now."""
        # TODO: Implement media service for URL generation
        return f"/media/{obj.storage_key}"


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ['id', 'index', 'block_type', 'config']


class PageSerializer(serializers.ModelSerializer):
    blocks = BlockSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = ['id', 'index', 'title', 'meta', 'blocks']


class ActivityVersionSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityVersion
        fields = ['id', 'version', 'title', 'description', 'meta', 'is_published', 'created_at', 'pages']


class ActivitySerializer(serializers.ModelSerializer):
    """List view of activities."""
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    latest_version_number = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'slug', 'title', 'description', 'status',
            'organization', 'organization_name',
            'latest_version_number', 'author_meta',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_latest_version_number(self, obj):
        """Get latest published version number."""
        latest = obj.versions.filter(is_published=True).order_by('-version').first()
        return latest.version if latest else None


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single activity."""
    activity_version = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'slug', 'title', 'description', 'status',
            'organization', 'organization_name',
            'activity_version', 'media', 'author_meta',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_activity_version(self, obj):
        """Get the latest published activity version with pages and blocks."""
        if hasattr(obj, '_prefetched_activity_version'):
            activity_version = obj._prefetched_activity_version
        else:
            activity_version = obj.versions.filter(
                is_published=True
            ).prefetch_related('pages__blocks').order_by('-version').first()

        if activity_version:
            return ActivityVersionSerializer(activity_version).data
        return None

    def get_media(self, obj):
        """Get all media assets referenced in this activity."""
        from ..services import MediaService

        # Get the latest published version
        activity_version = obj.versions.filter(is_published=True).order_by('-version').first()
        if not activity_version:
            return []

        # Extract media IDs from all blocks
        media_ids = set()
        for page in activity_version.pages.all():
            for block in page.blocks.all():
                if block.block_type == 'media' and 'media_id' in block.config:
                    media_ids.add(block.config['media_id'])
                elif block.block_type == 'question' and 'config' in block.config:
                    question_config = block.config.get('config', {})
                    if 'options' in question_config:
                        for option in question_config['options']:
                            if 'media_id' in option:
                                media_ids.add(option['media_id'])

        # Resolve media
        if media_ids:
            media_dict = MediaService.bulk_resolve_media(list(media_ids))
            return list(media_dict.values())

        return []