from typing import Dict, Any, List, Optional
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_curated_content():
    """
    Initialize directories and files for curated content.
    Call this during app startup to ensure directories exist.
    """
    base_dir = os.path.dirname(__file__)
    curated_dir = os.path.join(base_dir, 'curated_content')
    
    # Create directory if it doesn't exist
    if not os.path.exists(curated_dir):
        os.makedirs(curated_dir)
    
    # Create empty JSON files if they don't exist
    files_to_create = {
        'explanations.json': {'explanations': []},
        'hints.json': {}
    }
    
    for filename, default_content in files_to_create.items():
        file_path = os.path.join(curated_dir, filename)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_content, f, indent=2)
                logger.info(f"Created empty curated content file: {filename}")

def add_curated_explanation(concept: str, theme: str, age_group: str, explanation: str) -> bool:
    """
    Add a curated explanation to the curated content.
    
    Args:
        concept: The concept name
        theme: The theme
        age_group: Target age group
        explanation: The explanation text
        
    Returns:
        True if successful, False otherwise
    """
    file_path = os.path.join(os.path.dirname(__file__), 'curated_content', 'explanations.json')
    
    try:
        # Load existing content
        with open(file_path, 'r') as f:
            content = json.load(f)
        
        # Add new explanation
        content['explanations'].append({
            'concept': concept,
            'theme': theme,
            'age_group': age_group,
            'explanation': explanation
        })
        
        # Save back to file
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to add curated explanation: {str(e)}")
        return False

def add_curated_hint(challenge_id: int, hint_level: int, hint_text: str) -> bool:
    """
    Add a curated hint for a challenge.
    
    Args:
        challenge_id: The challenge ID
        hint_level: Hint level (1-3)
        hint_text: The hint text
        
    Returns:
        True if successful, False otherwise
    """
    file_path = os.path.join(os.path.dirname(__file__), 'curated_content', 'hints.json')
    
    try:
        # Load existing content
        with open(file_path, 'r') as f:
            content = json.load(f)
        
        # Ensure challenge ID exists in dictionary
        if str(challenge_id) not in content:
            content[str(challenge_id)] = {}
        
        # Add hint
        content[str(challenge_id)][str(hint_level)] = hint_text
        
        # Save back to file
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to add curated hint: {str(e)}")
        return False

def get_model_info() -> Dict[str, Any]:
    """
    Get information about the currently active model.
    
    Returns:
        Dictionary with model information
    """
    from .adapter import get_current_adapter
    
    adapter = get_current_adapter()
    
    return {
        'adapter_type': adapter.__class__.__name__,
        'is_mock': isinstance(adapter, MockAdapter) if 'MockAdapter' in globals() else False,
        'status': 'active'
    }