"""
Certificate extraction routes.
"""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import logging
from typing import Dict, Any
from injector import inject

from services.ocr_service import OCRService
from services.certificate_service import CertificateService
import config.settings as settings

logger = logging.getLogger(__name__)

certificate_bp = Blueprint('certificate', __name__, url_prefix='/api/v1/certificate')


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


@certificate_bp.route('/process', methods=['POST'])
@inject
def process_document(
    ocr_service: OCRService,
    certificate_service: CertificateService
):
    """
    Process certificate documents to extract structured information using OCR and LLM.
    
    This endpoint performs the complete document processing pipeline:
    1. OCR text extraction from the uploaded document
    2. Text preprocessing and cleaning
    3. LLM-based analysis for intelligent field extraction
    4. Structured data output
    
    Accepts PDF, PNG, JPEG, and other image formats.
    
    Returns:
        JSON with extracted fields like name, CPF, birth date, etc.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}'
            }), 400
        
        file_content = file.read()
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        logger.info(f"Processing file: {filename} ({len(file_content)} bytes)")
        
        # Extract text using OCR service
        extracted_text = ocr_service.process_file(file_content, file_extension)
        
        if not extracted_text.strip():
            return jsonify({'error': 'No text could be extracted from the document'}), 400
        
        logger.info(f"Total extracted text: {len(extracted_text)} characters")
        
        # Process certificate through complete pipeline (LLM + categorization)
        processing_result = certificate_service.process_certificate(extracted_text, filename)
        
        if not processing_result['success']:
            return jsonify({
                'error': processing_result['error'],
                'filename': filename
            }), 400
        
        response = {
            "success": True,
            "filename": filename,
            "extracted_fields": processing_result['extracted_fields'],
            "categorization": processing_result['categorization'],
            "text_length": len(extracted_text),
            "processing_pipeline": processing_result['processing_pipeline']
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing certificate: {e}")
        return jsonify({
            'error': f'Error processing document: {str(e)}'
        }), 500