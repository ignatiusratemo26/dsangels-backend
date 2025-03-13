from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone

from core.models import UserProgress, Content, Challenge, User
from core.serializers import UserProgressSerializer

class UserProgressListView(generics.ListAPIView):
    """
    List all progress records for the authenticated user
    """
    serializer_class = UserProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter progress records by the authenticated user"""
        return UserProgress.objects.filter(user=self.request.user).order_by('-started_at')

class UserProgressDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a progress record
    """
    serializer_class = UserProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only allow access to the user's own progress records"""
        return UserProgress.objects.filter(user=self.request.user)

class TrackCompletionView(APIView):
    """
    Track completion of content or challenge
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        content_id = request.data.get('content_id')
        challenge_id = request.data.get('challenge_id')
        completion_percentage = float(request.data.get('completion_percentage', 0))
        
        if not (content_id or challenge_id):
            return Response(
                {'error': 'Either content_id or challenge_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the relevant UserProgress instance
        if content_id:
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                content_id=content_id,
                defaults={'completion_percentage': 0}
            )
        else:
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                challenge_id=challenge_id,
                defaults={'completion_percentage': 0}
            )
        
        # Update completion percentage if it's higher than current
        if completion_percentage > progress.completion_percentage:
            progress.completion_percentage = completion_percentage
            
            # If completed (100%), set completed_at timestamp
            if completion_percentage >= 100:
                progress.completed_at = timezone.now()
                
                # Award points based on difficulty level
                if progress.challenge:
                    progress.points_earned = progress.challenge.points
                elif progress.content:
                    # Basic formula: Base points * difficulty multiplier
                    difficulty_multiplier = (progress.content.difficulty_base / 3) + 0.5
                    progress.points_earned = int(50 * difficulty_multiplier)
            
            progress.save()
        
        return Response(UserProgressSerializer(progress).data)

class UserStatsView(APIView):
    """
    Get statistics about user's learning progress
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get counts of completed and in-progress content
        completed_count = UserProgress.objects.filter(
            user=user,
            completion_percentage=100
        ).count()
        
        in_progress_count = UserProgress.objects.filter(
            user=user,
            completion_percentage__gt=0,
            completion_percentage__lt=100
        ).count()
        
        # Get total points earned
        total_points = UserProgress.objects.filter(
            user=user
        ).aggregate(points=Sum('points_earned'))['points'] or 0
        
        # Get average difficulty completed
        avg_difficulty = UserProgress.objects.filter(
            user=user,
            completion_percentage=100
        ).aggregate(
            avg_diff=Avg('content__difficulty_base')
        )['avg_diff'] or 0
        
        # Get most recently completed content
        recent_progress = UserProgress.objects.filter(
            user=user,
            completed_at__isnull=False
        ).order_by('-completed_at').first()
        
        recent_content = None
        if recent_progress:
            if recent_progress.content:
                recent_content = {
                    'id': recent_progress.content.id,
                    'title': recent_progress.content.title,
                    'type': 'content'
                }
            elif recent_progress.challenge:
                recent_content = {
                    'id': recent_progress.challenge.id,
                    'title': recent_progress.challenge.title,
                    'type': 'challenge'
                }
        
        return Response({
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'total_points': total_points,
            'average_difficulty': round(avg_difficulty, 1),
            'recent_completion': recent_content,
            'joined_days': (timezone.now().date() - user.date_joined.date()).days
        })

class LearningPathView(APIView):
    """
    Get recommended learning path for the user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get the user's age group
        age_group_id = request.user.age_group_id
        if not age_group_id:
            return Response(
                {'error': 'User does not have an assigned age group'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get content already completed by user
        completed_content_ids = UserProgress.objects.filter(
            user=request.user,
            completion_percentage=100
        ).values_list('content_id', flat=True)
        
        # Get appropriate content for user's age group they haven't completed yet
        learning_path = Content.objects.filter(
            age_group_id=age_group_id
        ).exclude(
            id__in=completed_content_ids
        ).order_by('difficulty_base')[:10]
        
        # Create path structure with modules
        path = []
        for i, content in enumerate(learning_path):
            path.append({
                'step': i + 1,
                'content_id': content.id,
                'title': content.title,
                'difficulty': content.difficulty_base,
                'estimated_time': f"{content.difficulty_base * 15}-{content.difficulty_base * 25} minutes",
                'content_type': content.content_type
            })
        
        return Response({
            'learning_path': path,
            'total_steps': len(path),
            'recommended_pace': '2-3 modules per week'
        })