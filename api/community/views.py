from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import ForumTopic, ForumPost, Comment, RoleModel, MentorConnection
from core.serializers import (
    ForumTopicSerializer, ForumPostSerializer, CommentSerializer,
    RoleModelSerializer, MentorConnectionSerializer
)

class ForumTopicListCreateView(generics.ListCreateAPIView):
    """
    List all forum topics or create a new one
    """
    queryset = ForumTopic.objects.all().order_by('-created_at')
    serializer_class = ForumTopicSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ForumTopicDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a forum topic
    """
    queryset = ForumTopic.objects.all()
    serializer_class = ForumTopicSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        # Only allow creators or staff to modify topics
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return ForumTopic.objects.filter(
                Q(created_by=self.request.user) | Q(created_by__is_staff=True)
            )
        return ForumTopic.objects.all()

class ForumPostListCreateView(generics.ListCreateAPIView):
    """
    List all posts for a specific topic or create a new post
    """
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        topic_id = self.kwargs['topic_id']
        return ForumPost.objects.filter(topic_id=topic_id).order_by('-created_at')
    
    def perform_create(self, serializer):
        topic_id = self.kwargs['topic_id']
        topic = get_object_or_404(ForumTopic, pk=topic_id)
        serializer.save(created_by=self.request.user, topic=topic)

class ForumPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a forum post
    """
    queryset = ForumPost.objects.all()
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        # Only allow creators or staff to modify posts
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return ForumPost.objects.filter(
                Q(created_by=self.request.user) | Q(created_by__is_staff=True)
            )
        return ForumPost.objects.all()

class CommentListCreateView(generics.ListCreateAPIView):
    """
    List all comments for a post or create a new comment
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).order_by('created_at')
    
    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(ForumPost, pk=post_id)
        serializer.save(created_by=self.request.user, post=post)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a comment
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        # Only allow creators or staff to modify comments
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return Comment.objects.filter(
                Q(created_by=self.request.user) | Q(created_by__is_staff=True)
            )
        return Comment.objects.all()

class MentorConnectionListView(generics.ListCreateAPIView):
    """
    List mentorship connections or create a new connection request
    """
    serializer_class = MentorConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can see connections they're part of
        user = self.request.user
        return MentorConnection.objects.filter(
            Q(mentee=user) | Q(mentor__user=user)
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        # User requesting the connection is the mentee
        serializer.save(mentee=self.request.user, status='pending')

class MentorConnectionDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a mentor connection
    """
    queryset = MentorConnection.objects.all()
    serializer_class = MentorConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see connections they're part of
        user = self.request.user
        return MentorConnection.objects.filter(
            Q(mentee=user) | Q(mentor__user=user)
        )
    
    def update(self, request, *args, **kwargs):
        connection = self.get_object()
        
        # Only the mentor can accept/reject connection requests
        if (request.data.get('status') in ['accepted', 'rejected'] and 
            connection.mentor.user != request.user):
            return Response(
                {'error': 'Only the mentor can accept or reject connection requests'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return super().update(request, *args, **kwargs)

class RoleModelListView(generics.ListCreateAPIView):
    """
    List women role models in tech to inspire users
    """
    queryset = RoleModel.objects.all().order_by('name')
    serializer_class = RoleModelSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = RoleModel.objects.all()
        
        # Filter by field if provided
        field = self.request.query_params.get('field')
        if field:
            queryset = queryset.filter(field__icontains=field)
            
        # Filter by country if provided
        country = self.request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
            
        return queryset.order_by('name')

class RoleModelDetailView(generics.RetrieveAPIView):
    """
    Retrieve details for a specific role model
    """
    queryset = RoleModel.objects.all()
    serializer_class = RoleModelSerializer
    permission_classes = [permissions.AllowAny]