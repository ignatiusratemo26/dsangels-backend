import logging
from django.db.models import Q, Count, Case, When, IntegerField, F
from collections import defaultdict
from core.models import Content, UserProgress, User

logger = logging.getLogger(__name__)

def get_personalized_recommendations(user_id, count=5, content_type=None):
    """
    Generate personalized content recommendations for a user
    
    Args:
        user_id (int): The user ID to generate recommendations for
        count (int): Number of recommendations to return
        content_type (str, optional): Filter by content type (lesson, challenge, etc.)
        
    Returns:
        list: List of dictionaries with content recommendations and scores
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's age group to filter appropriate content
        age_group_id = user.age_group_id
        
        # Get content the user has already interacted with
        completed_content_ids = UserProgress.objects.filter(
            user_id=user_id,
            completion_percentage__gte=80  # Consider "completed" if >= 80%
        ).values_list('content_id', flat=True)
        
        viewed_content_ids = UserProgress.objects.filter(
            user_id=user_id
        ).values_list('content_id', flat=True)
        
        # Base query - filter by age group and exclude completed content
        query = Content.objects.filter(age_group_id=age_group_id)
        
        if content_type:
            query = query.filter(content_type=content_type)
            
        # Exclude content the user has completed
        query = query.exclude(id__in=completed_content_ids)
        
        # Order content based on multiple factors
        recommended_content = query.annotate(
            # Content the user has started but not finished gets higher priority
            in_progress=Case(
                When(id__in=viewed_content_ids, then=10),
                default=0,
                output_field=IntegerField()
            ),
            # Consider difficulty - prefer content that's slightly above user's average completed difficulty
            relevance_score=Case(
                # This assumes content with difficulty close to user's level gets higher score
                # You'd want to replace this with actual logic based on user's history
                When(difficulty_base__lte=3, then=5),  # Example logic
                default=1,
                output_field=IntegerField()
            )
        ).order_by('-in_progress', '-relevance_score', 'difficulty_base', '-created_at')
        
        # Get the recommendations
        recommendations = recommended_content[:count]
        
        # Format the results
        result = []
        for item in recommendations:
            result.append({
                'content_id': item.id,
                'title': item.title,
                'content_type': item.content_type,
                'difficulty': item.difficulty_base,
                'relevance_score': item.relevance_score + item.in_progress
            })
            
        return result
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.exception(f"Error generating recommendations: {e}")
        return []