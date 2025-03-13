from django.urls import path
from .views import (
    UserActivityListView, 
    UserActivityCreateView,
    UserAnalyticsView, 
    ContentAnalyticsView,
    EngagementStatsView,
    ActivityTimelineView
)

urlpatterns = [
    path('user-activities/', UserActivityListView.as_view(), name='user-activity-list'),
    path('log-activity/', UserActivityCreateView.as_view(), name='log-activity'),
    path('user-stats/', UserAnalyticsView.as_view(), name='user-analytics'),
    path('content-stats/', ContentAnalyticsView.as_view(), name='content-analytics'),
    path('engagement-stats/', EngagementStatsView.as_view(), name='engagement-stats'),
    path('activity-timeline/', ActivityTimelineView.as_view(), name='activity-timeline'),
]