"""
LLM Service for handling Ollama interactions and field extraction.
"""
import requests
import json
import re
import logging
from typing import Dict, Any

import config.settings as settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for handling LLM operations with Ollama."""
    
    def __init__(self, prompt_service):
        """Initialize LLM service with prompt service dependency."""
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.connection_timeout = settings.OLLAMA_CONNECTION_TIMEOUT
        self.model_download_timeout = settings.MODEL_DOWNLOAD_TIMEOUT
        self.prompt_service = prompt_service
    
    def test_connection(self) -> bool:
        """Test if Ollama is available."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", 
                timeout=self.connection_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return False
    
    def ensure_model_available(self) -> bool:
        """Ensure the required model is available, download if not."""
        try:
            # Check if model is already available
            response = requests.get(
                f"{self.base_url}/api/tags", 
                timeout=self.connection_timeout
            )
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in models]
                
                if self.model in model_names:
                    logger.info(f"Model {self.model} is already available")
                    return True
                
                # Model not found, try to pull it
                logger.info(f"Model {self.model} not found, attempting to pull...")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model},
                    timeout=self.model_download_timeout
                )
                
                if pull_response.status_code == 200:
                    logger.info(f"Successfully pulled model {self.model}")
                    return True
                else:
                    logger.error(f"Failed to pull model {self.model}: {pull_response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ensuring model availability: {e}")
            return False
    
    def _parse_json_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        if '{' in llm_response and '}' in llm_response:
            start = llm_response.find('{')
            end = llm_response.rfind('}') + 1
            json_str = llm_response[start:end]
            
            logger.info(f"Extracted JSON string: {json_str}")
            
            extracted_data = json.loads(json_str)
            
            # Validate required fields exist
            required_fields = ['nome_participante', 'evento', 'local', 'data', 'carga_horaria']
            for field in required_fields:
                if field not in extracted_data:
                    extracted_data[field] = None
            
            logger.info("Successfully extracted fields using LLM (JSON format)")
            return extracted_data
        else:
            raise ValueError("No valid JSON found in response")
    
    def _parse_key_value_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse key-value format response from LLM."""
        logger.info("No JSON found, attempting to parse key-value format")
        extracted_data = {}
        required_fields = ['nome_participante', 'evento', 'local', 'data', 'carga_horaria']
        
        # Split response into lines and parse each field
        lines = llm_response.split('\n')
        current_field = None
        current_value = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with a field name
            field_found = False
            for field in required_fields:
                if line.lower().startswith(field.lower() + ':'):
                    # Save previous field if exists
                    if current_field and current_value:
                        extracted_data[current_field] = current_value.strip()
                    
                    # Start new field
                    current_field = field
                    current_value = line[len(field)+1:].strip()
                    field_found = True
                    break
            
            # If no field found, append to current value
            if not field_found and current_field:
                current_value += " " + line
        
        # Save the last field
        if current_field and current_value:
            extracted_data[current_field] = current_value.strip()
        
        # Ensure all required fields exist and clean values
        for field in required_fields:
            if field not in extracted_data:
                extracted_data[field] = None
            else:
                # Clean up the extracted value
                value = extracted_data[field]
                if value:
                    # Remove any trailing artifacts
                    value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                    value = re.sub(r'[^\w\sÀ-ÿ.,;:()\-/]', '', value)  # Remove special chars
                    extracted_data[field] = value.strip()
        
        logger.info("Successfully extracted fields using LLM (key-value format)")
        return extracted_data
    
    def extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract certificate fields using Ollama LLM."""
        try:
            # Get formatted prompt from prompt service
            prompt = self.prompt_service.get_certificate_extraction_prompt(text)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "top_p": 0.9
                }
            }
            
            logger.info(f"Sending request to Ollama with model: {self.model}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            logger.info(f"Ollama response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                
                logger.info(f"LLM raw response: {llm_response[:200]}...")
                
                # Try to parse JSON response first, then fallback to key-value
                try:
                    return self._parse_json_response(llm_response)
                except (json.JSONDecodeError, ValueError):
                    try:
                        return self._parse_key_value_response(llm_response)
                    except Exception as e:
                        logger.error(f"Failed to parse LLM response: {e}")
                        logger.error(f"LLM response was: {llm_response}")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                logger.error(f"Response content: {response.text}")
            
            return self._get_empty_fields()
                
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return self._get_empty_fields()
    
    def categorize_activity(
        self, 
        raw_text: str,
        extracted_data: Dict[str, Any],
        categories_text: str
    ) -> Dict[str, Any]:
        """
        Categorize activity using Ollama LLM with structured data.
        
        Args:
            raw_text: Complete OCR text from certificate
            extracted_data: Dictionary with extracted fields (nome_participante, evento, etc.)
            categories_text: Formatted string with available categories
            
        Returns:
            Dictionary with categorization results: {
                'category_id': int,
                'calculated_hours': int,
                'confidence': float,
                'reasoning': str
            }
        """
        try:
            # Build proper categorization prompt using PromptService
            prompt = self.prompt_service.get_activity_categorization_prompt(
                raw_text=raw_text,
                nome_participante=extracted_data.get('nome_participante', ''),
                evento=extracted_data.get('evento', ''),
                local=extracted_data.get('local', ''),
                data=extracted_data.get('data', ''),
                carga_horaria=extracted_data.get('carga_horaria', ''),
                categories_text=categories_text
            )
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent categorization
                    "top_p": 0.9
                }
            }
            
            logger.info(f"Sending categorization request to Ollama with model: {self.model}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            logger.info(f"Ollama categorization response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                
                logger.info(f"LLM categorization raw response: {llm_response[:200]}...")
                
                # Parse the categorization response
                return self._parse_categorization_response(llm_response)
            else:
                logger.error(f"Ollama API error for categorization: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return self._get_empty_categorization()
                
        except Exception as e:
            logger.error(f"Error calling Ollama for categorization: {e}")
            return self._get_empty_categorization()
    
    def _parse_categorization_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse categorization response from LLM."""
        # Try to parse JSON response first
        try:
            if '{' in llm_response and '}' in llm_response:
                start = llm_response.find('{')
                end = llm_response.rfind('}') + 1
                json_str = llm_response[start:end]
                
                categorization_data = json.loads(json_str)
                
                # Ensure required fields exist with defaults
                return {
                    'category_id': categorization_data.get('category_id'),
                    'calculated_hours': categorization_data.get('calculated_hours'),
                    'confidence': categorization_data.get('confidence'),
                    'reasoning': categorization_data.get('reasoning', llm_response)
                }
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: try to extract information from text
        logger.info("No JSON found in categorization response, using fallback parsing")
        return {
            'category_id': None,
            'calculated_hours': None,
            'confidence': None,
            'reasoning': llm_response
        }
    
    def _get_empty_categorization(self) -> Dict[str, Any]:
        """Return empty categorization structure."""
        return {
            'category_id': None,
            'calculated_hours': None,
            'confidence': None,
            'reasoning': None
        }
    
    def _get_empty_fields(self) -> Dict[str, Any]:
        """Return empty fields structure."""
        return {
            'nome_participante': None,
            'evento': None,
            'local': None,
            'data': None,
            'carga_horaria': None
        }