"""
Certificate Service for handling certificate-specific operations.
"""
import logging
from typing import Dict, Any
from services.llm_service import LLMService
from services.activity_categorization_service import ActivityCategorizationService

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for handling certificate-specific operations."""
    
    def __init__(self, llm_service: LLMService, activity_categorization_service: ActivityCategorizationService):
        self.llm_service = llm_service
        self.activity_categorization_service = activity_categorization_service
    
    def process_certificate(self, text: str, filename: str = None) -> Dict[str, Any]:
        """
        Process certificate text through complete pipeline:
        1. Extract fields using LLM
        2. Categorize activity and calculate valid hours
        
        Args:
            text: OCR extracted text
            filename: Original filename
            
        Returns:
            Complete processing results
        """
        try:
            # Step 1: Extract fields using LLM
            extracted_fields = self.llm_service.extract_fields(text)
            
            if not extracted_fields:
                return {
                    'success': False,
                    'error': 'Failed to extract fields from text',
                    'extracted_fields': {},
                    'categorization': {}
                }
            
            # Add filename and raw text for categorization
            extracted_fields['filename'] = filename
            extracted_fields['raw_text'] = text
            
            # Step 2: Categorize activity and calculate hours
            categorization_result = self.activity_categorization_service.categorize_activity(extracted_fields)
            
            # Step 3: Format response
            return {
                'success': True,
                'extracted_fields': extracted_fields,
                'categorization': categorization_result,
                'processing_pipeline': ['llm_extraction', 'activity_categorization']
            }
            
        except Exception as e:
            logger.error(f"Error processing certificate: {e}")
            return {
                'success': False,
                'error': f'Certificate processing failed: {str(e)}',
                'extracted_fields': {},
                'categorization': {}
            }

