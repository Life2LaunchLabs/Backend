from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, GuestLead


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        email = validated_data.get('email')
        user = User.objects.create_user(**validated_data)

        # Check for existing GuestLead with this email and link it
        try:
            guest_lead = GuestLead.objects.filter(email=email, converted_to_user__isnull=True).first()
            if guest_lead:
                guest_lead.mark_as_converted(user)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Linked GuestLead {guest_lead.id} to new user {user.email}")
        except Exception as e:
            # Don't fail user creation if lead linking fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to link guest lead for {email}: {e}")

        # Initialize default quests for new user using V2 system
        from apps.quests.default_quests_v2 import initialize_default_quests_for_user_v2
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting quest initialization for user {user.email}")

        try:
            result = initialize_default_quests_for_user_v2(user)
            if result:
                enrollment_count = len([k for k in result.keys() if 'enrollment' in k])
                logger.info(f"✅ Successfully initialized default quests for user {user.email}: {enrollment_count} enrollments created")
                logger.info(f"Created: {list(result.keys())}")
            else:
                logger.warning(f"⚠️ Quest initialization returned empty result for user {user.email}")
        except Exception as e:
            # Log the error with full traceback but don't fail user creation
            logger.error(f"❌ Failed to initialize default quests for user {user.email}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')

        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for authentication responses"""
    full_name = serializers.CharField(source='get_full_name_with_middle', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'date_joined', 'is_active', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'date_joined', 'is_active', 'is_staff', 'is_superuser')


class PublicProfileSerializer(serializers.ModelSerializer):
    """Public profile data safe for API responses - no sensitive PII"""
    profile_photo_url = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='get_anonymous_display_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'anonymous_id', 'display_name', 'bio',
            'profile_photo_url', 'account_created'
        )
        read_only_fields = ('anonymous_id', 'account_created')
    
    def get_profile_photo_url(self, obj):
        """Return profile photo URL if available"""
        if obj.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_photo.url)
            return obj.profile_photo.url
        return None


class PrivateProfileSerializer(serializers.ModelSerializer):
    """Full profile data for authenticated user's own profile"""
    full_name = serializers.CharField(source='get_full_name_with_middle', read_only=True)
    profile_photo_url = serializers.SerializerMethodField()
    encrypted_data = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'middle_name', 'last_name',
            'full_name', 'bio', 'tagline', 'birth_date', 'profile_photo_url',
            'account_created', 'anonymous_id', 'encrypted_data'
        )
        read_only_fields = ('id', 'account_created', 'anonymous_id')
    
    def get_profile_photo_url(self, obj):
        """Return profile photo URL if available"""
        if obj.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_photo.url)
            return obj.profile_photo.url
        return None
    
    def get_encrypted_data(self, obj):
        """Return decrypted sensitive data for user's own profile"""
        # Only return encrypted data for the requesting user
        request = self.context.get('request')
        if request and request.user == obj:
            return obj.get_encrypted_data()
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information"""

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email',
            'bio', 'tagline', 'birth_date', 'profile_photo'
        )

    def validate_email(self, value):
        """Ensure email is unique if being changed"""
        if value:
            user = self.instance
            if User.objects.exclude(pk=user.pk).filter(email=value).exists():
                raise serializers.ValidationError("Email already in use")
        return value


class GuestLeadSerializer(serializers.ModelSerializer):
    """Serializer for creating guest leads from onboarding flow"""

    class Meta:
        model = GuestLead
        fields = ('id', 'email', 'subscribed_to_updates', 'flow_id', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_email(self, value):
        """Validate email format and check for duplicates"""
        if not value:
            raise serializers.ValidationError("Email is required")

        # Check if email already exists as a GuestLead
        if GuestLead.objects.filter(email=value).exists():
            # Allow update, not a strict error
            pass

        return value

    def create(self, validated_data):
        """Create or update guest lead with session data"""
        email = validated_data['email']

        # Get or create to handle duplicate email submissions
        guest_lead, created = GuestLead.objects.update_or_create(
            email=email,
            defaults={
                'subscribed_to_updates': validated_data.get('subscribed_to_updates', True),
                'flow_id': validated_data.get('flow_id', 'user-onboarding-v1'),
                'session_key': validated_data.get('session_key'),
                'guest_attempt_ids': validated_data.get('guest_attempt_ids', {}),
            }
        )

        return guest_lead


