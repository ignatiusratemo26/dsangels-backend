from typing import Dict, Any, List, Optional
import logging
from .adapter import get_current_adapter

logger = logging.getLogger(__name__)

def generate_chat_response(message: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a chat response based on user input and context
    
    Args:
        message: User's message
        user_data: Dictionary with user context (age_group, name, interests, etc.)
        
    Returns:
        Dictionary with response data
    """
    adapter = get_current_adapter()
    age_group = user_data.get('age_group', {}).get('name', 'General')
    age_range = user_data.get('age_group', {}).get('age_range', '8-18')
    username = user_data.get('display_name', 'friend')
    chat_history = user_data.get('chat_history', [])[-5:]  # Get last 5 messages for context
    
    # Format chat history for the prompt
    history_text = ""
    if chat_history:
        for entry in chat_history:
            if entry.get('is_user'):
                history_text += f"User: {entry.get('message')}\n"
            else:
                history_text += f"Mowgli: {entry.get('message')}\n"
    
    # Create prompt based on age group and context
    if '8-10' in age_range:
        tone = "very friendly, simple vocabulary, enthusiastic, uses emojis, encouraging"
        explanation_style = "using very simple analogies like comparing code to recipes or building blocks"
    elif '11-13' in age_range:
        tone = "friendly, slightly more mature vocabulary, encouraging, occasional emoji"
        explanation_style = "using relatable analogies like social media, games, or hobbies"
    else:  # 14+ 
        tone = "friendly but more mature, conversational, encouraging"
        explanation_style = "using more precise technical terms but still with helpful analogies"
    
    prompt = f"""
    You are Mowgli, a friendly AI tech guide for the DSAngels platform, which helps young girls learn coding and tech skills.
    You're chatting with {username}, who is in the {age_group} age group ({age_range} years old).
    
    Your personality:
    - You are friendly, supportive, and encouraging
    - You speak in a {tone} tone
    - You explain technical concepts {explanation_style}
    - You promote coding, tech careers, and female role models in technology
    - You never use inappropriate language or discuss inappropriate topics
    - You keep your answers concise and helpful for young learners
    
    Recent chat history:
    {history_text}
    
    User: {message}
    Mowgli:
    """
    
    try:
        response = adapter.generate_text(
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        
        return {
            'message': response,
            'success': True
        }
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        return {
            'message': "I'm having trouble thinking right now. Let's chat again in a moment!",
            'success': False,
            'error': str(e)
        }