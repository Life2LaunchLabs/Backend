from django.urls import path
from . import views

urlpatterns = [
    # Phase 1 Basic endpoints
    path('send/', views.ChatView.as_view(), name='chat_send'),
    
    # Session management
    path('sessions/', views.SessionListView.as_view(), name='chat_sessions'),
    path('sessions/create/', views.SessionCreateView.as_view(), name='chat_session_create'),
    path('sessions/<str:session_id>/', views.SessionDetailView.as_view(), name='chat_session_detail'),
    
    # Message history
    path('sessions/<str:session_id>/history/', views.MessageHistoryView.as_view(), name='chat_message_history'),
    
    # Configuration and validation
    path('presets/', views.PresetInfoView.as_view(), name='chat_presets'),
    path('validate-preset/', views.PresetValidationView.as_view(), name='chat_validate_preset'),
    path('provider-status/', views.ProviderStatusView.as_view(), name='chat_provider_status'),
    
    # Phase 3 Analytics endpoints
    path('analytics/', views.ConversationAnalyticsView.as_view(), name='chat_analytics'),
    path('sessions/<str:session_id>/insights/', views.SessionInsightsView.as_view(), name='chat_session_insights'),
    path('analytics/provider-comparison/', views.ProviderComparisonView.as_view(), name='chat_provider_comparison'),
]