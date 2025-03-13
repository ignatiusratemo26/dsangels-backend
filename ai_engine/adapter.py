import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union, Optional
import json
import logging
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelAdapter(ABC):
    """
    Abstract base class for adapting different LLM models.
    Implement this interface for each LLM model you want to support.
    """
    
    @abstractmethod
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 200, 
                     temperature: float = 0.7) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The prompt to generate from
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (higher = more random)
            
        Returns:
            Generated text as string
        """
        pass
    
    @abstractmethod
    def classify_content(self, 
                        content: str, 
                        categories: List[str]) -> Dict[str, float]:
        """
        Classify content into provided categories.
        
        Args:
            content: The content to classify
            categories: List of category names
            
        Returns:
            Dictionary of category->confidence score mappings
        """
        pass


class OpenAIAdapter(ModelAdapter):
    """
    Adapter for OpenAI API (GPT models)
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI adapter.
        
        Args:
            model: Model to use (e.g., "gpt-3.5-turbo", "gpt-4")
        """
        # Get API key from environment variable
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            raise ValueError("OpenAI API key not found")
        
        self.model = model
        self.base_url = "https://api.openai.com/v1/"
        logger.info(f"Initialized OpenAI adapter with model: {model}")
    
    def generate_text(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                urljoin(self.base_url, "chat/completions"),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            return "I couldn't generate a response at this time."
    
    def classify_content(self, content: str, categories: List[str]) -> Dict[str, float]:
        # Create a prompt for zero-shot classification
        categories_str = ", ".join(categories)
        prompt = f"""
        Classify the following content into one of these categories: {categories_str}
        
        Content: {content}
        
        Respond with a JSON object containing the category as the key and confidence score (0-1) as the value.
        Example: {{"category_name": 0.8}}
        """
        
        try:
            result_text = self.generate_text(prompt, max_tokens=100, temperature=0.1)
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'{.*}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                # If no valid JSON found, return equal probabilities
                return {category: 1.0/len(categories) for category in categories}
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {category: 0.0 for category in categories}


class CohereAdapter(ModelAdapter):
    """
    Adapter for Cohere API
    """
    
    def __init__(self, model: str = "command"):
        """
        Initialize the Cohere adapter.
        
        Args:
            model: Model to use (e.g., "command", "command-light")
        """
        # Get API key from environment variable
        self.api_key = os.environ.get("COHERE_API_KEY")
        if not self.api_key:
            logger.error("Cohere API key not found. Set COHERE_API_KEY environment variable.")
            raise ValueError("Cohere API key not found")
        
        self.model = model
        self.base_url = "https://api.cohere.ai/v1/"
        logger.info(f"Initialized Cohere adapter with model: {model}")
    
    def generate_text(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                urljoin(self.base_url, "generate"),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["generations"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Cohere API request failed: {str(e)}")
            return "I couldn't generate a response at this time."
    
    def classify_content(self, content: str, categories: List[str]) -> Dict[str, float]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "inputs": [content],
            "examples": [],
            "task_type": "classification",
            "output_indicators": categories
        }
        
        try:
            response = requests.post(
                urljoin(self.base_url, "classify"),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Convert probabilities to dictionary
            classifications = result["classifications"][0]
            return {
                label: confidence 
                for label, confidence in zip(
                    classifications["labels"], 
                    classifications["confidences"]
                )
            }
        except Exception as e:
            logger.error(f"Cohere classification failed: {str(e)}")
            return {category: 0.0 for category in categories}


class AnthropicAdapter(ModelAdapter):
    """
    Adapter for Anthropic Claude API
    """
    
    def __init__(self, model: str = "claude-2"):
        """
        Initialize the Anthropic adapter.
        
        Args:
            model: Model to use (e.g., "claude-2", "claude-instant-1")
        """
        # Get API key from environment variable
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.error("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            raise ValueError("Anthropic API key not found")
        
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/"
        logger.info(f"Initialized Anthropic adapter with model: {model}")
    
    def generate_text(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                urljoin(self.base_url, "complete"),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["completion"].strip()
        except Exception as e:
            logger.error(f"Anthropic API request failed: {str(e)}")
            return "I couldn't generate a response at this time."
    
    def classify_content(self, content: str, categories: List[str]) -> Dict[str, float]:
        # Create a prompt for zero-shot classification
        categories_str = ", ".join(categories)
        prompt = f"""
        Classify the following content into one of these categories: {categories_str}
        
        Content: {content}
        
        Respond with a JSON object containing the category as the key and confidence score (0-1) as the value.
        Example: {{"category_name": 0.8}}
        """
        
        try:
            result_text = self.generate_text(prompt, max_tokens=100, temperature=0.1)
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'{.*}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                # If no valid JSON found, return equal probabilities
                return {category: 1.0/len(categories) for category in categories}
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {category: 0.0 for category in categories}


class HuggingFaceInferenceAPIAdapter(ModelAdapter):
    """
    Adapter for Hugging Face Inference API (hosted models)
    """
    
    def __init__(self, model_id: str = "gpt2"):
        """
        Initialize the Hugging Face Inference API adapter.
        
        Args:
            model_id: The model ID on Hugging Face Hub
        """
        # Get API key from environment variable
        self.api_key = os.environ.get("HF_API_KEY")
        if not self.api_key:
            logger.error("Hugging Face API key not found. Set HF_API_KEY environment variable.")
            raise ValueError("Hugging Face API key not found")
        
        self.model_id = model_id
        self.base_url = f"https://api-inference.huggingface.co/models/"
        logger.info(f"Initialized Hugging Face Inference API adapter with model: {model_id}")
    
    def generate_text(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{self.model_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "generated_text" in result[0]:
                    return result[0]["generated_text"].strip()
                else:
                    return str(result[0]).strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            logger.error(f"Hugging Face Inference API request failed: {str(e)}")
            return "I couldn't generate a response at this time."
    
    def classify_content(self, content: str, categories: List[str]) -> Dict[str, float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            # Use a zero-shot classification model
            classification_model = "facebook/bart-large-mnli"
            
            payload = {
                "inputs": content,
                "parameters": {
                    "candidate_labels": categories
                }
            }
            
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{classification_model}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Convert to dictionary
            return {
                label: score 
                for label, score in zip(result["labels"], result["scores"])
            }
            
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {category: 0.0 for category in categories}


class HuggingFaceAdapter(ModelAdapter):
    """
    Adapter for Hugging Face models using the transformers library.
    """
    # ...existing implementation...


class MockAdapter(ModelAdapter):
    """
    Mock adapter for testing or when no AI service is available.
    """
    # ...existing implementation...


# Factory function to get the appropriate adapter
def get_model_adapter(adapter_type: str = "mock", **kwargs) -> ModelAdapter:
    """
    Factory function to get the appropriate model adapter.
    
    Args:
        adapter_type: Type of adapter ("openai", "cohere", "anthropic", 
                                     "huggingface_api", "huggingface", "mock")
        **kwargs: Additional parameters for the specific adapter
        
    Returns:
        An instance of ModelAdapter
    """
    if adapter_type.lower() == "openai":
        return OpenAIAdapter(**kwargs)
    elif adapter_type.lower() == "cohere":
        return CohereAdapter(**kwargs)
    elif adapter_type.lower() == "anthropic":
        return AnthropicAdapter(**kwargs)
    elif adapter_type.lower() == "huggingface_api":
        return HuggingFaceInferenceAPIAdapter(**kwargs)
    elif adapter_type.lower() == "huggingface":
        return HuggingFaceAdapter(**kwargs)
    elif adapter_type.lower() == "mock":
        return MockAdapter(**kwargs)
    else:
        logger.warning(f"Unknown adapter type: {adapter_type}. Using mock adapter.")
        return MockAdapter(**kwargs)

# Current active adapter instance (singleton)
_current_adapter = None

def get_current_adapter() -> ModelAdapter:
    """
    Get the current global adapter instance.
    Creates a new one if it doesn't exist.
    
    Returns:
        ModelAdapter instance
    """
    global _current_adapter
    if _current_adapter is None:
        # Get adapter settings from Django settings
        from django.conf import settings
        
        adapter_type = getattr(settings, 'AI_ENGINE', {}).get('ADAPTER_TYPE', 'mock')
        
        # Get model name from settings if specified
        model_kwargs = {}
        model_name = getattr(settings, 'AI_ENGINE', {}).get('MODEL_NAME')
        
        if model_name:
            if adapter_type.lower() == "openai":
                model_kwargs["model"] = model_name
            elif adapter_type.lower() == "cohere":
                model_kwargs["model"] = model_name
            elif adapter_type.lower() == "anthropic":
                model_kwargs["model"] = model_name
            elif adapter_type.lower() in ["huggingface", "huggingface_api"]:
                model_kwargs["model_id"] = model_name
        
        # Pass API key through environment variable or directly 
        api_key = getattr(settings, 'AI_ENGINE', {}).get('API_KEY')
        if api_key:
            # Set the appropriate environment variable based on the adapter type
            if adapter_type.lower() == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif adapter_type.lower() == "cohere":
                os.environ["COHERE_API_KEY"] = api_key
            elif adapter_type.lower() == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif adapter_type.lower() in ["huggingface", "huggingface_api"]:
                os.environ["HF_API_KEY"] = api_key
                
        _current_adapter = get_model_adapter(adapter_type, **model_kwargs)
    return _current_adapter