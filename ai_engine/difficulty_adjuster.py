import logging
from .adapter import AIModelAdapter
from core.models import UserProgress

logger = logging.getLogger(__name__)
ai_adapter = AIModelAdapter()

def adjust_content_difficulty(content, target_difficulty):
    """
    Adjust the difficulty of content to match the user's learning level
    
    Args:
        content: Content object to adjust
        target_difficulty (int): Target difficulty level (1-5)
        
    Returns:
        dict: Adjusted content with modified fields
    """
    current_difficulty = content.difficulty_base
    
    # If already at target difficulty, return unchanged
    if current_difficulty == target_difficulty:
        return {
            'title': content.title,
            'description': content.description,
            'difficulty': current_difficulty,
            'adjusted': False
        }
    
    # Determine if we're making it easier or harder
    making_easier = target_difficulty < current_difficulty
    
    prompt = f"""
    I need to adjust the following content to make it {"easier" if making_easier else "more challenging"}.
    
    Original content (difficulty level {current_difficulty}/5):
    Title: {content.title}
    Description: {content.description}
    
    Please rewrite this content for difficulty level {target_difficulty}/5, where 1 is very easy and 5 is very challenging.
    Make these adjustments:
    1. Simplify/enhance the vocabulary
    2. Make explanations {"more detailed with examples" if making_easier else "more concise and advanced"}
    3. {"Break concepts into smaller steps" if making_easier else "Combine concepts and provide fewer steps"}
    4. Adjust the title slightly to reflect the new difficulty level
    
    Return your response in JSON format like this:
    {{
        "title": "adjusted title",
        "description": "adjusted description"
    }}
    """
    
    try:
        response = ai_adapter.generate_text(prompt, max_tokens=800)
        
        # Try to parse the JSON response
        import json
        try:
            adjusted_content = json.loads(response)
            return {
                'title': adjusted_content.get('title', content.title),
                'description': adjusted_content.get('description', content.description),
                'original_difficulty': current_difficulty,
                'difficulty': target_difficulty,
                'adjusted': True
            }
        except json.JSONDecodeError:
            # Return a structured response with the generated text as description
            return {
                'title': content.title,
                'description': response,  # Use the generated text as description
                'original_difficulty': current_difficulty,
                'difficulty': target_difficulty,
                'adjusted': True
            }
    except Exception as e:
        logger.error(f"Error adjusting content difficulty: {e}")
        return {
            'title': content.title,
            'description': content.description,
            'difficulty': current_difficulty,
            'error': str(e),
            'adjusted': False
        }

def get_appropriate_difficulty_level(user_id):
    """
    Determine appropriate difficulty level for a user based on their history
    
    Args:
        user_id (int): ID of the user
        
    Returns:
        int: Recommended difficulty level (1-5)
    """
    try:
        # Get user's completed content
        completed_progress = UserProgress.objects.filter(
            user_id=user_id,
            completion_percentage__gte=75  # Consider "completed" if >= 75%
        )
        
        if not completed_progress.exists():
            # New user, start with easiest content
            return 1
            
        # Get average difficulty of successfully completed content
        from django.db.models import Avg
        avg_difficulty = completed_progress.aggregate(
            avg_diff=Avg('content__difficulty_base')
        )['avg_diff'] or 1
        
        # Round to nearest integer and ensure within 1-5 range
        recommended_difficulty = max(1, min(5, round(avg_difficulty)))
        
        # If user is consistently doing well (high completion), suggest slightly harder content
        high_performance = completed_progress.filter(
            completion_percentage__gte=90
        ).count() / completed_progress.count() >= 0.7  # 70% of completed content with high scores
        
        if high_performance:
            recommended_difficulty = min(5, recommended_difficulty + 1)
            
        return recommended_difficulty
        
    except Exception as e:
        logger.error(f"Error determining appropriate difficulty: {e}")
        return 1  # Default to easiest as fallback