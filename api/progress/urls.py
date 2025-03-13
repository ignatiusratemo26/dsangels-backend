from django.urls import path
from .views import (
    UserProgressListView, UserProgressDetailView, 
    TrackCompletionView, UserStatsView,
    LearningPathView
)

urlpatterns = [
    path('', UserProgressListView.as_view(), name='user-progress-list'),
    path('<int:pk>/', UserProgressDetailView.as_view(), name='user-progress-detail'),
    path('track-completion/', TrackCompletionView.as_view(), name='track-completion'),
    path('stats/', UserStatsView.as_view(), name='user-stats'),
    path('learning-path/', LearningPathView.as_view(), name='learning-path'),
]