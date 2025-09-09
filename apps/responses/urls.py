from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseSessionViewSet

router = DefaultRouter()
router.register(r'sessions', CourseSessionViewSet, basename='coursesession')

urlpatterns = [
    path('', include(router.urls)),
]