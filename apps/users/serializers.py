from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for authentication responses"""
    full_name = serializers.CharField(source='get_full_name_with_middle', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'email', 'date_joined', 'is_active')
        read_only_fields = ('id', 'date_joined', 'is_active')


class PublicProfileSerializer(serializers.ModelSerializer):
    """Public profile data safe for API responses - no sensitive PII"""
    profile_photo_url = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='get_anonymous_display_name', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'anonymous_id', 'username', 'display_name', 'bio', 
            'profile_photo_url', 'account_created'
        )
        read_only_fields = ('anonymous_id', 'username', 'account_created')
    
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
            'id', 'username', 'email', 'first_name', 'middle_name', 'last_name',
            'full_name', 'bio', 'birth_date', 'profile_photo_url', 
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
            'first_name', 'middle_name', 'last_name', 'email', 
            'bio', 'birth_date', 'profile_photo'
        )
    
    def validate_email(self, value):
        """Ensure email is unique if being changed"""
        if value:
            user = self.instance
            if User.objects.exclude(pk=user.pk).filter(email=value).exists():
                raise serializers.ValidationError("Email already in use")
        return value


class UsernameCheckSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    
    def validate_username(self, value):
        # Just validate format, don't check availability here
        if not value:
            raise serializers.ValidationError("Username is required")
        return value