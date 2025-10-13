"""
Certificate Service for handling certificate-specific operations.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for handling certificate-specific operations."""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    def extract_certificate_info(self, text: str) -> Dict[str, Any]:
        """Extract certificate information from text using LLM."""
        try:
            # Use LLM-based extraction with built-in text cleaning
            extracted_fields = self.llm_service.extract_fields(text)
            
            # Format the response to match the expected API structure
            results = {}
            extraction_method = "llm"
            
            for field_name, value in extracted_fields.items():
                results[field_name] = {
                    "value": value,
                    "extraction_method": extraction_method
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error in certificate extraction: {e}")
            # Return empty structure on error
            return {
                field: {
                    "value": None,
                    "extraction_method": "error"
                } for field in ['nome_participante', 'evento', 'local', 'data', 'carga_horaria']
            }
