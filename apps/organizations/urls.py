from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrganizationViewSet, AdminStatusView, SetDefaultOrganizationView

# Create the main router
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)

urlpatterns = [
    # Admin status endpoints
    path('admin/status/', AdminStatusView.as_view(), name='admin-status'),
    path('admin/set-default-org/', SetDefaultOrganizationView.as_view(), name='set-default-org'),

    # Include all the viewset routes
    path('', include(router.urls)),
]