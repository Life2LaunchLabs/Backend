from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.ChatView.as_view(), name='chat_send'),
]