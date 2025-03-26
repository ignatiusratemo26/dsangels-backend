from django.urls import path
from .views import (
    BadgeListView, BadgeDetailView, 
    UserBadgesView, LeaderboardView,
    AwardBadgeView, TrackPointsView
)

urlpatterns = [
    path('badges/', BadgeListView.as_view(), name='badge-list'),
    path('badges/<int:pk>/', BadgeDetailView.as_view(), name='badge-detail'),
    path('user-badges/', UserBadgesView.as_view(), name='user-badges'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('award-badge/', AwardBadgeView.as_view(), name='award-badge'),
    path('track-points/', TrackPointsView.as_view(), name='track-points'),
]