from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, F
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from core.models import UserActivity, Challenge, ConceptNote

from core.models import Badge, User, UserProgress
from core.serializers import BadgeSerializer

class BadgeListView(generics.ListAPIView):
    """
    List all available badges
    """
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class BadgeDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific badge
    """
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class UserBadgesView(APIView):
    """
    List badges earned by the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get badges earned by user
        badges = user.badges.all()
        
        # Show progress toward unearned badges
        all_badges = Badge.objects.all()
        unearned_badges = []
        
        for badge in all_badges:
            if badge not in badges:
                # Check progress toward each badge
                progress = self.calculate_badge_progress(user, badge)
                unearned_badges.append({
                    'id': badge.id,
                    'name': badge.name,
                    'description': badge.description,
                    'image_url': badge.image_url,
                    'points_value': badge.points_value,
                    'progress': progress,
                    'is_achievement': badge.is_achievement
                })
        
        return Response({
            'earned_badges': BadgeSerializer(badges, many=True).data,
            'unearned_badges': unearned_badges
        })
    
    def calculate_badge_progress(self, user, badge):
        """Calculate user's progress toward earning a badge"""
        # This is a simplified version - you'd make this match your badge requirements
        if badge.is_achievement:
            # For achievements, check requirements
            requirements = badge.requirements.all()
            if not requirements:
                return 0
            
            completed = 0
            for req in requirements:
                if req.requirement_type == 'content_completion':
                    # Check if user has completed specific content
                    content_id = req.requirement_data.get('content_id')
                    if content_id:
                        progress = UserProgress.objects.filter(
                            user=user, 
                            content_id=content_id,
                            completion_percentage=100
                        ).exists()
                        if progress:
                            completed += 1
                
                elif req.requirement_type == 'challenge_completion':
                    # Check if user has completed specific challenge
                    challenge_id = req.requirement_data.get('challenge_id')
                    if challenge_id:
                        progress = UserProgress.objects.filter(
                            user=user, 
                            challenge_id=challenge_id,
                            completion_percentage=100
                        ).exists()
                        if progress:
                            completed += 1
                
                elif req.requirement_type == 'points_threshold':
                    # Check if user has enough points
                    threshold = req.threshold
                    points = UserProgress.objects.filter(user=user).aggregate(
                        total=Sum('points_earned')
                    )['total'] or 0
                    if points >= threshold:
                        completed += 1
            
            return (completed / len(requirements)) * 100
        
        return 0

class LeaderboardView(APIView):
    """
    Get leaderboard of users based on points
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get top users by points
        top_users = User.objects.annotate(
            total_points=Sum('progresses__points_earned')
        ).order_by('-total_points')[:10]
        
        # Get requesting user's rank
        user_points = UserProgress.objects.filter(user=request.user).aggregate(
            total=Sum('points_earned')
        )['total'] or 0
        
        user_rank = User.objects.annotate(
            total_points=Sum('progresses__points_earned')
        ).filter(
            total_points__gt=user_points
        ).count() + 1
        
        # Format the response
        leaderboard = []
        for i, user in enumerate(top_users):
            leaderboard.append({
                'rank': i + 1,
                'username': user.username,
                'display_name': user.display_name or user.username,
                'points': user.total_points or 0,
                'is_current_user': user.id == request.user.id
            })
        
        return Response({
            'leaderboard': leaderboard,
            'current_user_rank': user_rank,
            'current_user_points': user_points
        })



class TrackPointsView(APIView):
    """
    Track points earned from user activities
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        activity_type = request.data.get('activity_type')
        points = request.data.get('points', 0)
        metadata = request.data.get('metadata', {})
        
        if not activity_type:
            return Response(
                {'error': 'Activity type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find related content object if provided
        content_object = None
        content_type = None
        object_id = None
        
        if 'challenge_id' in metadata:
            try:
                challenge_id = metadata['challenge_id']
                # Convert to integer if it's a string
                if isinstance(challenge_id, str):
                    challenge_id = int(challenge_id)
                content_object = Challenge.objects.get(id=challenge_id)
                content_type = ContentType.objects.get_for_model(Challenge)
                object_id = challenge_id
            except (Challenge.DoesNotExist, ValueError):
                pass
                
        elif 'concept_id' in metadata:
            try:
                concept_id = metadata['concept_id']
                # Convert to integer if it's a string
                if isinstance(concept_id, str):
                    concept_id = int(concept_id)
                content_object = ConceptNote.objects.get(id=concept_id)
                content_type = ContentType.objects.get_for_model(ConceptNote)
                object_id = concept_id
            except (ConceptNote.DoesNotExist, ValueError):
                pass
        
        # Clean up metadata to ensure it's serializable
        cleaned_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                cleaned_metadata[key] = value
        
        # Create activity record directly
        activity = UserActivity.objects.create(
            user=user,
            activity_type='points',
            content_type=content_type,
            object_id=object_id,
            data={
                'points_earned': points,
                'source_activity': activity_type,
                'metadata': cleaned_metadata
            }
        )
        
        # Get updated points total for the user by extracting from the data JSONField
        user_activities = UserActivity.objects.filter(
            user=user,
            activity_type='points'
        )
        
        # Calculate total points by summing up points_earned from the data field
        total_points = 0
        for act in user_activities:
            try:
                points_value = act.data.get('points_earned', 0)
                if isinstance(points_value, (int, float)):
                    total_points += points_value
            except (AttributeError, TypeError):
                # Skip activities with missing or invalid data
                pass
        
        # Check if user qualifies for new badges based on points
        badges_awarded = []
        if points > 0:
            # This is simplified - you might want to add more logic here
            for badge in Badge.objects.filter(requirements__requirement_type='points_threshold'):
                if badge not in user.badges.all():
                    for req in badge.requirements.filter(requirement_type='points_threshold'):
                        if total_points >= req.threshold:
                            user.badges.add(badge)
                            badges_awarded.append(badge)
                            break
        
        response_data = {
            'success': True,
            'points_earned': points,
            'total_points': total_points
        }
        
        if badges_awarded:
            response_data['badges_awarded'] = BadgeSerializer(badges_awarded, many=True).data
            response_data['message'] = f"You earned {len(badges_awarded)} new badge(s)!"
        
        return Response(response_data)
    
    
class AwardBadgeView(APIView):
    """
    Check if user qualifies for badges and award them
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Get user's current badges
        current_badges = user.badges.all()
        
        # Get all badges the user doesn't have yet
        badges_to_check = Badge.objects.exclude(id__in=current_badges.values_list('id', flat=True))
        
        newly_awarded = []
        
        # Check each badge to see if user qualifies
        for badge in badges_to_check:
            if self.user_qualifies_for_badge(user, badge):
                # Award the badge
                user.badges.add(badge)
                newly_awarded.append(badge)
        
        if newly_awarded:
            return Response({
                'awarded': BadgeSerializer(newly_awarded, many=True).data,
                'message': f"Congratulations! You earned {len(newly_awarded)} new badge(s)."
            })
        
        return Response({'message': "No new badges earned."})
    
    def user_qualifies_for_badge(self, user, badge):
        """Check if a user qualifies for a specific badge"""
        requirements = badge.requirements.all()
        if not requirements:
            return False
        
        # Check each requirement
        for req in requirements:
            if req.requirement_type == 'content_completion':
                # Check content completion requirement
                content_id = req.requirement_data.get('content_id')
                if content_id:
                    has_completed = UserProgress.objects.filter(
                        user=user,
                        content_id=content_id,
                        completion_percentage=100
                    ).exists()
                    if not has_completed:
                        return False
                else:
                    # Check if user completed X number of content items
                    count_required = req.threshold
                    count_completed = UserProgress.objects.filter(
                        user=user,
                        content__isnull=False,
                        completion_percentage=100
                    ).count()
                    if count_completed < count_required:
                        return False
            
            elif req.requirement_type == 'challenge_completion':
                # Check challenge completion requirement
                challenge_id = req.requirement_data.get('challenge_id')
                if challenge_id:
                    has_completed = UserProgress.objects.filter(
                        user=user,
                        challenge_id=challenge_id,
                        completion_percentage=100
                    ).exists()
                    if not has_completed:
                        return False
                else:
                    # Check if user completed X number of challenges
                    count_required = req.threshold
                    count_completed = UserProgress.objects.filter(
                        user=user,
                        challenge__isnull=False,
                        completion_percentage=100
                    ).count()
                    if count_completed < count_required:
                        return False
            
            elif req.requirement_type == 'points_threshold':
                # Check points threshold requirement
                threshold = req.threshold
                points = UserProgress.objects.filter(user=user).aggregate(
                    total=Sum('points_earned')
                )['total'] or 0
                if points < threshold:
                    return False
            
            else:
                
                pass
            
            # Add other requirement types as needed
        
        # If we got here, all requirements are met
        return True