from rest_framework import serializers
from .models import Organization, OrganizationAdmin


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrganizationAdminSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationAdmin relationship"""
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationAdmin
        fields = ['organization', 'role', 'permissions', 'created_at']
        read_only_fields = ['created_at']


class UserAdminStatusSerializer(serializers.Serializer):
    """Serializer for user admin status response"""
    is_admin = serializers.BooleanField()
    admin_organizations = OrganizationSerializer(many=True)
    default_organization = OrganizationSerializer(allow_null=True)