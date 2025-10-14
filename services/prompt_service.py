"""
Prompt service for managing LLM prompt templates and formatting.
"""
from typing import Dict, Any
import logging

from config.prompts import CERTIFICATE_EXTRACTION_PROMPT, ACTIVITY_CATEGORIZATION_PROMPT

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing and formatting LLM prompt templates."""
    
    def __init__(self):
        """Initialize prompt service."""
        self.prompts = {
            'certificate_extraction': CERTIFICATE_EXTRACTION_PROMPT,
            'activity_categorization': ACTIVITY_CATEGORIZATION_PROMPT
        }
    
    def get_prompt(self, prompt_type: str, **kwargs) -> str:
        """
        Get a formatted prompt by type.
        
        Args:
            prompt_type: The type of prompt to retrieve
            **kwargs: Variables to format into the prompt template
            
        Returns:
            Formatted prompt string
            
        Raises:
            ValueError: If prompt type is not found
        """
        if prompt_type not in self.prompts:
            available_types = list(self.prompts.keys())
            raise ValueError(f"Unknown prompt type '{prompt_type}'. Available types: {available_types}")
        
        template = self.prompts[prompt_type]
        
        try:
            formatted_prompt = template.format(**kwargs)
            logger.debug(f"Generated prompt for type '{prompt_type}' with {len(kwargs)} parameters")
            return formatted_prompt
        except KeyError as e:
            raise ValueError(f"Missing required parameter for prompt '{prompt_type}': {e}")
    
    def get_certificate_extraction_prompt(self, text: str) -> str:
        """
        Get formatted certificate extraction prompt.
        
        Args:
            text: OCR extracted text to process
            
        Returns:
            Formatted certificate extraction prompt
        """
        return self.get_prompt('certificate_extraction', text=text)
    
    def get_activity_categorization_prompt(
        self, 
        raw_text: str,
        nome_participante: str,
        evento: str,
        local: str,
        data: str,
        carga_horaria: str,
        categories_text: str
    ) -> str:
        """
        Get formatted activity categorization prompt.
        
        Args:
            raw_text: Complete OCR text
            nome_participante: Participant name
            evento: Event name
            local: Location
            data: Date
            carga_horaria: Hours
            categories_text: Formatted categories list
            
        Returns:
            Formatted activity categorization prompt
        """
        return self.get_prompt(
            'activity_categorization',
            raw_text=raw_text,
            nome_participante=nome_participante,
            evento=evento,
            local=local,
            data=data,
            carga_horaria=carga_horaria,
            categories_text=categories_text
        )
    
    def list_available_prompts(self) -> list:
        """List all available prompt types."""
        return list(self.prompts.keys())
    
    def add_prompt(self, prompt_type: str, template: str) -> None:
        """
        Add a new prompt template dynamically.
        
        Args:
            prompt_type: Unique identifier for the prompt
            template: Prompt template string with format placeholders
        """
        self.prompts[prompt_type] = template
        logger.info(f"Added new prompt type: '{prompt_type}'")