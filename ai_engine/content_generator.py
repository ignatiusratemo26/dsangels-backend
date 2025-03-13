from typing import Dict, Any, Optional, List
import logging
from .adapter import get_current_adapter
from django.core.cache import cache
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache duration in seconds (24 hours)
CACHE_DURATION = 86400

def generate_themed_explanation(
    concept: str, 
    theme: str = "general", 
    age_group: Optional[str] = None,
    base_explanation: Optional[str] = None
) -> str:
    """
    Generate a themed explanation for a technical concept.
    
    Args:
        concept: The technical concept to explain
        theme: Theme to use for the explanation (e.g., "princess", "space", "nature")
        age_group: Target age group (e.g., "Kids 5-8", "Teens 13-16")
        base_explanation: Optional base explanation to enhance
        
    Returns:
        Themed explanation of the concept
    """
    # Try to get from cache first
    cache_key = f"themed_explanation:{concept}:{theme}:{age_group}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Retrieved themed explanation from cache: {cache_key}")
        return cached_result
    
    # Check if we have pre-curated content first
    curated_explanation = _get_curated_explanation(concept, theme, age_group)
    if curated_explanation:
        cache.set(cache_key, curated_explanation, CACHE_DURATION)
        return curated_explanation
    
    # Create prompt based on the inputs
    age_context = f" for {age_group}" if age_group else ""
    prompt = f"""
    Please explain the programming concept of '{concept}' using a {theme} theme{age_context}.
    Make it engaging, visual, and easy to understand.
    Use metaphors related to {theme} to make the concept relatable.
    """
    
    # If we have a base explanation, include it for the AI to enhance
    if base_explanation:
        prompt += f"\n\nHere's a basic explanation to enhance: {base_explanation}"
    
    # Generate the explanation
    try:
        adapter = get_current_adapter()
        explanation = adapter.generate_text(
            prompt=prompt,
            max_tokens=400,
            temperature=0.7
        )
        
        # Cache the result
        cache.set(cache_key, explanation, CACHE_DURATION)
        return explanation
        
    except Exception as e:
        logger.error(f"Failed to generate themed explanation: {str(e)}")
        # Fall back to base explanation or a default message
        return base_explanation or f"Sorry, I couldn't generate a {theme}-themed explanation for {concept} right now."

def generate_hint(
    challenge_id: int, 
    user_id: Optional[int] = None, 
    user_attempt: str = "", 
    hint_level: int = 1
) -> str:
    """
    Generate a hint for a coding challenge.
    
    Args:
        challenge_id: ID of the challenge
        user_id: ID of the user (for personalization)
        user_attempt: User's current code attempt (optional)
        hint_level: Level of hint detail (1=subtle, 3=more specific)
        
    Returns:
        A hint for the challenge
    """
    # Try to get from cache first
    cache_key = f"hint:{challenge_id}:{hint_level}"
    cached_result = cache.get(cache_key)
    if cached_result and not user_attempt:  # Only use cache if no user attempt is provided
        logger.info(f"Retrieved hint from cache: {cache_key}")
        return cached_result
    
    # Check if we have pre-curated hints first
    curated_hint = _get_curated_hint(challenge_id, hint_level)
    if curated_hint and not user_attempt:
        cache.set(cache_key, curated_hint, CACHE_DURATION)
        return curated_hint
    
    # If user attempt is provided, create a personalized hint
    if user_attempt:
        try:
            # Get challenge details from database
            from core.models import Challenge
            challenge = Challenge.objects.get(id=challenge_id)


            prompt = f"""
            Problem: {challenge.problem_statement}
            
            Expected Output: {challenge.expected_output}
            
            User's current code attempt:
            {user_attempt}
            
            Provide a hint at level {hint_level} (1=subtle, 3=more specific) to help the user solve this problem.
            Don't give the direct answer, just guide them in the right direction.
            """
            
            adapter = get_current_adapter()
            hint = adapter.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.5
            )
            return hint
            
        except Exception as e:
            logger.error(f"Failed to generate personalized hint: {str(e)}")
            # Fall back to generic hint
            pass
    
    # Generate generic hint based on challenge
    try:
        from core.models import Challenge
        challenge = Challenge.objects.get(id=challenge_id)
        
        prompt = f"""
        Problem: {challenge.problem_statement}
        
        Provide a hint at level {hint_level} (1=subtle, 3=more specific) to help solve this problem.
        Don't give the direct answer, just guide the user in the right direction.
        """
        
        adapter = get_current_adapter()
        hint = adapter.generate_text(
            prompt=prompt,
            max_tokens=150,
            temperature=0.5
        )
        
        # Cache the generic hint
        if not user_attempt:
            cache.set(cache_key, hint, CACHE_DURATION)
            
        return hint
        
    except Exception as e:
        logger.error(f"Failed to generate hint: {str(e)}")
        return f"Try thinking about the problem step by step. What is the first thing you need to do?"

def adapt_content_difficulty(
    content_id: int, 
    user_id: Optional[int] = None, 
    target_difficulty: int = 3
) -> Dict[str, Any]:
    """
    Adapt content difficulty based on target level.
    
    Args:
        content_id: ID of the content to adapt
        user_id: ID of the user (for personalization)
        target_difficulty: Target difficulty level (1-5)
        
    Returns:
        Dictionary with adapted content
    """
    try:
        from core.models import Content
        content = Content.objects.get(id=content_id)
        
        # Try to get from cache first
        cache_key = f"adapted_content:{content_id}:{target_difficulty}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Retrieved adapted content from cache: {cache_key}")
            return json.loads(cached_result)
        
        # If target difficulty matches existing difficulty, no need to adapt
        if content.difficulty_base == target_difficulty:
            result = {
                'title': content.title,
                'description': content.description,
                'difficulty': content.difficulty_base,
                'adapted': False
            }
            cache.set(cache_key, json.dumps(result), CACHE_DURATION)
            return result
        
        # Generate prompt for adaptation
        change_direction = "simpler" if target_difficulty < content.difficulty_base else "more complex"
        prompt = f"""
        Original content: {content.title}
        Description: {content.description}
        Current difficulty level: {content.difficulty_base} (out of 5)
        
        Please adapt this content to make it {change_direction}, at a difficulty level of {target_difficulty} out of 5.
        Preserve the main learning objectives but adjust the complexity accordingly.
        Return the content as a title and description only.
        """
        
        adapter = get_current_adapter()
        adaptation = adapter.generate_text(
            prompt=prompt,
            max_tokens=300,
            temperature=0.4
        )
        
        # Parse the adaptation (this could be improved with more structured output from the model)
        import re
        title_match = re.search(r"Title[:\s]+(.*)", adaptation)
        description_match = re.search(r"Description[:\s]+(.*)", adaptation, re.DOTALL)
        
        adapted_title = title_match.group(1) if title_match else content.title
        adapted_description = description_match.group(1) if description_match else adaptation
        
        result = {
            'title': adapted_title,
            'description': adapted_description,
            'original_difficulty': content.difficulty_base,
            'target_difficulty': target_difficulty,
            'adapted': True
        }
        
        # Cache the result
        cache.set(cache_key, json.dumps(result), CACHE_DURATION)
        return result
        
    except Exception as e:
        logger.error(f"Failed to adapt content difficulty: {str(e)}")
        return {
            'error': f"Could not adapt content: {str(e)}",
            'original_title': content.title if 'content' in locals() else "Unknown",
            'adapted': False
        }

# Helper functions for curated content

def _get_curated_explanation(concept: str, theme: str, age_group: Optional[str]) -> Optional[str]:
    """
    Get pre-curated explanation from file or database.
    
    Returns None if no curated content is found.
    """
    curated_content_path = os.path.join(os.path.dirname(__file__), 'curated_content', 'explanations.json')
    
    try:
        if os.path.exists(curated_content_path):
            with open(curated_content_path, 'r') as file:
                content = json.load(file)
                
                # Look for matching content
                for item in content.get('explanations', []):
                    if (item.get('concept', '').lower() == concept.lower() and 
                        item.get('theme', '') == theme and
                        (age_group is None or item.get('age_group', '') == age_group)):
                        return item.get('explanation', '')
    except Exception as e:
        logger.error(f"Failed to load curated explanations: {str(e)}")
    
    return None

def _get_curated_hint(challenge_id: int, hint_level: int) -> Optional[str]:
    """
    Get pre-curated hint from file or database.
    
    Returns None if no curated hint is found.
    """
    curated_content_path = os.path.join(os.path.dirname(__file__), 'curated_content', 'hints.json')
    
    try:
        if os.path.exists(curated_content_path):
            with open(curated_content_path, 'r') as file:
                content = json.load(file)
                
                # Look for matching hint
                challenge_hints = content.get(str(challenge_id), {})
                return challenge_hints.get(str(hint_level))
    except Exception as e:
        logger.error(f"Failed to load curated hints: {str(e)}")
    
    return None