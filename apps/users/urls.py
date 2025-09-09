from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('check-username/', views.check_username, name='check_username'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]