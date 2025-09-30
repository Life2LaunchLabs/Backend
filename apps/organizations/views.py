from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Organization, OrganizationAdmin
from .serializers import OrganizationSerializer, UserAdminStatusSerializer


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Organization model - read-only for now"""
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'


class AdminStatusView(APIView):
    """View to check user's admin status and organizations"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's admin status"""
        user = request.user
        admin_orgs = user.get_admin_organizations()

        data = {
            'is_admin': user.is_organization_admin(),
            'admin_organizations': admin_orgs,
            'default_organization': user.get_default_admin_organization()
        }

        serializer = UserAdminStatusSerializer(data)
        return Response(serializer.data)


class SetDefaultOrganizationView(APIView):
    """View to set user's default organization"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Set the user's default organization"""
        org_slug = request.data.get('organization_slug')
        if not org_slug:
            return Response(
                {'error': 'organization_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            organization = Organization.objects.get(slug=org_slug, is_active=True)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is admin of this organization
        if not request.user.admin_organizations.filter(id=organization.id).exists():
            return Response(
                {'error': 'You are not an admin of this organization'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Set as default
        success = request.user.set_default_organization(organization)
        if success:
            return Response({
                'message': 'Default organization updated',
                'default_organization': OrganizationSerializer(organization).data
            })
        else:
            return Response(
                {'error': 'Failed to set default organization'},
                status=status.HTTP_400_BAD_REQUEST
            )
