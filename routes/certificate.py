"""
Certificate extraction routes.
"""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from typing import Dict, Any
from injector import inject

from services.ocr_service import OCRService
from services.certificate_service import CertificateService
from services.certificate_submission_service import CertificateSubmissionService
import config.settings as settings

logger = logging.getLogger(__name__)

certificate_bp = Blueprint('certificate', __name__, url_prefix='/api/v1/certificate')


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


@certificate_bp.route('/submit', methods=['POST'])
@inject
def submit_certificate(certificate_submission_service: CertificateSubmissionService):
    """
    Submit certificate for async processing.
    
    This endpoint:
    1. Validates the uploaded file and enrollment number
    2. Delegates processing to CertificateSubmissionService
    3. Returns appropriate HTTP response
    
    Required form data:
    - file: Certificate file (PDF, PNG, JPG, etc.)
    - enrollment_number: Student enrollment number
    
    Returns:
        JSON with submission details and tracking ID
    """
    try:
        # Validate request data
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        if 'enrollment_number' not in request.form:
            return jsonify({'error': 'Enrollment number is required'}), 400
        
        file = request.files['file']
        enrollment_number = request.form['enrollment_number'].strip()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not enrollment_number:
            return jsonify({'error': 'Enrollment number cannot be empty'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}'
            }), 400
        
        # Read file content
        file_content = file.read()
        original_filename = secure_filename(file.filename)
        mime_type = file.mimetype or 'application/octet-stream'
        
        logger.info(f"Submitting certificate: {original_filename} for {enrollment_number}")
        
        # Delegate to service layer
        success, result = certificate_submission_service.submit_certificate(
            file_content=file_content,
            original_filename=original_filename,
            enrollment_number=enrollment_number,
            mime_type=mime_type
        )
        
        if success:
            return jsonify({
                'success': True,
                **result
            }), 201
        else:
            # Check if it's a duplicate error (409) or other error (400/500)
            if result.get('error') == 'Duplicate file detected':
                return jsonify(result), 409
            elif 'Failed to queue file for processing' in result.get('error', ''):
                return jsonify(result), 500
            else:
                return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Unexpected error in submit_certificate: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@certificate_bp.route('/status/<int:submission_id>', methods=['GET'])
@inject
def get_submission_status(submission_id: int, certificate_submission_service: CertificateSubmissionService):
    """
    Get the status of a certificate submission.
    
    Args:
        submission_id: ID of the certificate submission
    
    Returns:
        JSON with submission status and processing details
    """
    try:
        success, result = certificate_submission_service.get_submission_status(submission_id)
        
        if success:
            return jsonify(result), 200
        else:
            if result.get('error') == 'Submission not found':
                return jsonify(result), 404
            else:
                return jsonify(result), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in get_submission_status: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@certificate_bp.route('/student/<enrollment_number>/submissions', methods=['GET'])
@inject
def get_student_submissions(enrollment_number: str, certificate_submission_service: CertificateSubmissionService):
    """
    Get all submissions for a specific student.
    
    Args:
        enrollment_number: Student enrollment number
    
    Query Parameters:
        status: Optional status filter
        limit: Maximum number of submissions to return (default: 50)
    
    Returns:
        JSON with list of student submissions
    """
    try:
        # Get query parameters
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        if limit > 100:  # Prevent excessive queries
            limit = 100
        
        success, result = certificate_submission_service.get_student_submissions(
            enrollment_number=enrollment_number,
            status=status_filter,
            limit=limit
        )
        
        if success:
            return jsonify(result), 200
        else:
            if result.get('error') == 'Student not found':
                return jsonify(result), 404
            else:
                return jsonify(result), 500
    
    except ValueError:
        return jsonify({'error': 'Invalid limit parameter'}), 400
    except Exception as e:
        logger.error(f"Unexpected error in get_student_submissions: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500