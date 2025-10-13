"""
Health check routes for the application.
"""
from flask import Blueprint, jsonify
import requests
import logging
from injector import inject

from services.llm_service import LLMService
import config.settings as settings

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api/v1')


@health_bp.route('/health', methods=['GET'])
@inject
def health_check(llm_service: LLMService):
    """Health check endpoint."""
    # Check Ollama and model availability in real time
    ollama_status = llm_service.test_connection()
    model_status = False
    
    if ollama_status:
        try:
            response = requests.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags", 
                timeout=settings.OLLAMA_CONNECTION_TIMEOUT
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in models]
                model_status = settings.OLLAMA_MODEL in model_names
        except:
            pass
    
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "api_version": "v1",
        "ollama_available": ollama_status,
        "ollama_model": settings.OLLAMA_MODEL,
        "model_downloaded": model_status,
        "tesseract_available": True
    })