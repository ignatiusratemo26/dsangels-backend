from django.urls import path
from .views import (
    ForumTopicListCreateView, ForumTopicDetailView,
    ForumPostListCreateView, ForumPostDetailView,
    MentorConnectionListView, MentorConnectionDetailView,
    RoleModelListView, RoleModelDetailView,
    CommentListCreateView, CommentDetailView
)

urlpatterns = [
    # Forum Topics
    path('topics/', ForumTopicListCreateView.as_view(), name='forum-topic-list'),
    path('topics/<int:pk>/', ForumTopicDetailView.as_view(), name='forum-topic-detail'),
    
    # Forum Posts
    path('topics/<int:topic_id>/posts/', ForumPostListCreateView.as_view(), name='forum-post-list'),
    path('posts/<int:pk>/', ForumPostDetailView.as_view(), name='forum-post-detail'),
    
    # Comments on posts
    path('posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='comment-list'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    
    # Mentor connections
    path('mentors/', MentorConnectionListView.as_view(), name='mentor-connection-list'),
    path('mentors/<int:pk>/', MentorConnectionDetailView.as_view(), name='mentor-connection-detail'),
    
    # Role models (inspiring women in tech)
    path('role-models/', RoleModelListView.as_view(), name='role-model-list'),
    path('role-models/<int:pk>/', RoleModelDetailView.as_view(), name='role-model-detail'),
]