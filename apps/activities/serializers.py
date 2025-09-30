from rest_framework import serializers
from .models import (
    MediaAsset, QuestionPackage, Activity, ActivityVersion,
    Page, Block, QuestDefinition, QuestInstance, Attempt,
    PageProgress, Response, ActivitySession, ActivitySubmission, SubmissionResponse
)
from .services import MediaService
from apps.organizations.serializers import OrganizationSerializer


class MediaAssetSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = ['id', 'storage_key', 'mime_type', 'width', 'height',
                 'duration_ms', 'meta', 'url', 'created_at']
        read_only_fields = ['id', 'storage_key', 'created_at']

    def get_url(self, obj):
        return MediaService.get_media_url(obj)


class MediaAssetCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    meta = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data):
        file = validated_data['file']
        meta = validated_data.get('meta', {})

        file_content = file.read()
        return MediaService.create_media_asset(file_content, file.name, meta)


class MediaResolver(serializers.Serializer):
    """Serializer for resolving multiple media IDs to their metadata."""
    media_id = serializers.UUIDField()
    url = serializers.URLField()
    mime_type = serializers.CharField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    duration_ms = serializers.IntegerField(allow_null=True)
    meta = serializers.JSONField()


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
    versions = ActivityVersionSerializer(many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Activity
        fields = ['id', 'slug', 'title', 'description', 'status', 'organization', 'author_meta',
                 'created_at', 'updated_at', 'versions', 'latest_version']

    def get_latest_version(self, obj):
        latest = obj.versions.filter(is_published=True).order_by('-version').first()
        if latest:
            return ActivityVersionSerializer(latest).data
        return None

    def get_title(self, obj):
        """Get title from latest published version."""
        return obj.title

    def get_description(self, obj):
        """Get description from latest published version."""
        return obj.description


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single activity with resolved media."""
    activity_version = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'slug', 'title', 'description', 'activity_version', 'media']

    def get_title(self, obj):
        """Get title from latest published version."""
        return obj.title

    def get_description(self, obj):
        """Get description from latest published version."""
        return obj.description

    def get_activity_version(self, obj):
        """Get the latest published activity version."""
        if hasattr(obj, '_prefetched_activity_version'):
            activity_version = obj._prefetched_activity_version
        else:
            activity_version = obj.versions.filter(is_published=True).order_by('-version').first()

        if activity_version:
            return ActivityVersionSerializer(activity_version).data
        return None

    def get_media(self, obj):
        """Resolve all media IDs found in blocks to their metadata."""
        media_ids = set()

        # Extract media IDs from all blocks in the activity
        if hasattr(obj, '_prefetched_activity_version'):
            activity_version = obj._prefetched_activity_version
        else:
            activity_version = obj.versions.filter(is_published=True).order_by('-version').first()

        if activity_version:
            for page in activity_version.pages.all():
                for block in page.blocks.all():
                    if block.block_type == 'media' and 'media_id' in block.config:
                        media_ids.add(block.config['media_id'])
                    elif block.block_type == 'question' and 'config' in block.config:
                        # Look for media in question options (e.g., image choice questions)
                        question_config = block.config.get('config', {})
                        if 'options' in question_config:
                            for option in question_config['options']:
                                if 'media_id' in option:
                                    media_ids.add(option['media_id'])

        # Resolve media IDs to metadata
        if media_ids:
            media_data = MediaService.bulk_resolve_media(list(media_ids))
            return list(media_data.values())
        return []


class QuestionPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionPackage
        fields = ['id', 'name', 'version', 'meta', 'created_at']


class QuestDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestDefinition
        fields = ['id', 'slug', 'name', 'rules', 'created_at']


class QuestInstanceSerializer(serializers.ModelSerializer):
    quest_definition = QuestDefinitionSerializer(read_only=True)

    class Meta:
        model = QuestInstance
        fields = ['id', 'quest_definition', 'items', 'status', 'created_at']


class AttemptSerializer(serializers.ModelSerializer):
    activity_version = ActivityVersionSerializer(read_only=True)
    quest_instance = QuestInstanceSerializer(read_only=True)

    class Meta:
        model = Attempt
        fields = ['id', 'activity_version', 'quest_instance', 'status',
                 'started_at', 'completed_at', 'meta']


class AttemptCreateSerializer(serializers.Serializer):
    activity_version_id = serializers.UUIDField()
    quest_instance_id = serializers.UUIDField(required=False, allow_null=True)
    meta = serializers.JSONField(required=False, default=dict)

    def validate_activity_version_id(self, value):
        try:
            activity_version = ActivityVersion.objects.get(id=value, is_published=True)
            return value
        except ActivityVersion.DoesNotExist:
            raise serializers.ValidationError("Activity version not found or not published.")

    def create(self, validated_data):
        user = self.context['request'].user
        activity_version = ActivityVersion.objects.get(id=validated_data['activity_version_id'])
        quest_instance = None

        if validated_data.get('quest_instance_id'):
            try:
                quest_instance = QuestInstance.objects.get(
                    id=validated_data['quest_instance_id'],
                    user=user
                )
            except QuestInstance.DoesNotExist:
                pass

        return Attempt.objects.create(
            user=user,
            activity_version=activity_version,
            quest_instance=quest_instance,
            meta=validated_data.get('meta', {})
        )


class PageProgressSerializer(serializers.ModelSerializer):
    page = PageSerializer(read_only=True)

    class Meta:
        model = PageProgress
        fields = ['page', 'reached', 'last_seen_at', 'data']


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['id', 'question_id', 'question_type', 'value', 'valid', 'meta', 'created_at']


class ResponseCreateSerializer(serializers.Serializer):
    question_id = serializers.CharField(max_length=128)
    question_type = serializers.CharField(max_length=50)
    page_id = serializers.UUIDField()
    value = serializers.JSONField()
    valid = serializers.BooleanField(default=True)
    meta = serializers.JSONField(required=False, default=dict)

    def validate_page_id(self, value):
        try:
            Page.objects.get(id=value)
            return value
        except Page.DoesNotExist:
            raise serializers.ValidationError("Page not found.")

    def create(self, validated_data):
        attempt = self.context['attempt']
        page = Page.objects.get(id=validated_data['page_id'])

        # Update or create response
        response, created = Response.objects.update_or_create(
            attempt=attempt,
            question_id=validated_data['question_id'],
            page=page,
            defaults={
                'question_type': validated_data['question_type'],
                'value': validated_data['value'],
                'valid': validated_data['valid'],
                'meta': validated_data.get('meta', {})
            }
        )
        return response


class BatchResponseCreateSerializer(serializers.Serializer):
    responses = ResponseCreateSerializer(many=True)

    def create(self, validated_data):
        attempt = self.context['attempt']
        created_responses = []

        for response_data in validated_data['responses']:
            serializer = ResponseCreateSerializer(data=response_data, context={'attempt': attempt})
            if serializer.is_valid(raise_exception=True):
                response = serializer.save()
                created_responses.append(response)

        return created_responses


# New serializers for improved session/submission architecture

class ActivitySubmissionSerializer(serializers.ModelSerializer):
    activity_version = ActivityVersionSerializer(read_only=True)
    quest_instance = QuestInstanceSerializer(read_only=True)

    class Meta:
        model = ActivitySubmission
        fields = ['id', 'activity_version', 'quest_instance', 'started_at',
                 'completed_at', 'time_taken', 'meta']


class SubmissionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionResponse
        fields = ['id', 'question_id', 'question_type', 'value', 'valid', 'meta', 'created_at']


class ActivitySubmissionDetailSerializer(serializers.ModelSerializer):
    activity_version = ActivityVersionSerializer(read_only=True)
    quest_instance = QuestInstanceSerializer(read_only=True)
    responses = SubmissionResponseSerializer(many=True, read_only=True)

    class Meta:
        model = ActivitySubmission
        fields = ['id', 'activity_version', 'quest_instance', 'started_at',
                 'completed_at', 'time_taken', 'meta', 'responses']


class ActivitySessionSerializer(serializers.ModelSerializer):
    activity_version = ActivityVersionSerializer(read_only=True)

    class Meta:
        model = ActivitySession
        fields = ['id', 'activity_version', 'current_page_index', 'session_data',
                 'last_activity', 'expires_at']