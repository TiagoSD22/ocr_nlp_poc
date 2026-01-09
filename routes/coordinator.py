"""
Coordinator review routes for certificate processing workflow.
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from injector import inject

from database.connection import get_db_session
from repositories.student_repository import StudentRepository
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from repositories.certificate_ocr_text_repository import CertificateOcrTextRepository
from repositories.certificate_metadata_repository import CertificateMetadataRepository
from repositories.extracted_activity_repository import ExtractedActivityRepository
from repositories.activity_category_repository import ActivityCategoryRepository
from services.s3_service import S3Service

logger = logging.getLogger(__name__)

coordinator_bp = Blueprint('coordinator', __name__, url_prefix='/api/v1/coordinator')


@coordinator_bp.route('/pending', methods=['GET'])
@inject
def get_pending_submissions(
    submission_repository: CertificateSubmissionRepository,
    student_repository: StudentRepository,
    ocr_text_repository: CertificateOcrTextRepository,
    metadata_repository: CertificateMetadataRepository,
    activity_repository: ExtractedActivityRepository,
    s3_service: S3Service
):
    """
    Get all certificate submissions pending coordinator review.
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - enrollment: Filter by enrollment number
    - status: Filter by status (pending_review, approved, rejected)
    
    Returns:
        JSON with paginated list of submissions pending review
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        enrollment_filter = request.args.get('enrollment')
        status_filter = request.args.get('status', 'pending_review')
        
        with get_db_session() as session:
            # Get pending submissions with pagination
            submissions, total = submission_repository.get_pending_submissions(
                session=session,
                status=status_filter,
                enrollment_filter=enrollment_filter,
                page=page,
                per_page=per_page
            )
            
            # Build response
            results = []
            for submission in submissions:
                # Get student info
                student = student_repository.get_by_id(session, submission.student_id)
                
                # Get metadata
                metadata = metadata_repository.get_by_submission_id(session, submission.id)
                
                # Get extracted activity
                activity = activity_repository.get_by_submission_id(session, submission.id)
                
                submission_data = {
                    'submission_id': submission.id,
                    'student_name': student.name if student else None,
                    'enrollment_number': student.enrollment_number if student else None,
                    'original_filename': submission.original_filename,
                    'submitted_at': submission.submitted_at.isoformat(),
                    'status': submission.status,
                    'metadata': {
                        'event_name': metadata.event_name if metadata else None,
                        'participant_name': metadata.participant_name if metadata else None,
                        'location': metadata.location if metadata else None,
                        'event_date': metadata.event_date if metadata else None,
                        'original_hours': metadata.original_hours if metadata else None,
                        'numeric_hours': metadata.numeric_hours if metadata else None
                    } if metadata else None,
                    'extracted_activity': {
                        'category_name': activity.category.name if activity and activity.category else None,
                        'calculated_hours': activity.calculated_hours if activity else None,
                        'llm_reasoning': activity.llm_reasoning if activity else None
                    } if activity else None
                }
                
                # Add presigned URL for file download
                if submission.s3_key:
                    try:
                        presigned_url = s3_service.generate_presigned_url(submission.s3_key)
                        submission_data['download_url'] = presigned_url
                    except Exception as e:
                        logger.warning(f"Failed to generate presigned URL for submission {submission.id}: {e}")
                        submission_data['download_url'] = None
                else:
                    submission_data['download_url'] = None
                
                results.append(submission_data)
            
            return jsonify({
                'success': True,
                'data': results,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting pending submissions: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve pending submissions'
        }), 500


@coordinator_bp.route('/submission/<int:submission_id>', methods=['GET'])
@inject
def get_submission_details(
    submission_id: int,
    submission_repository: CertificateSubmissionRepository,
    student_repository: StudentRepository,
    ocr_text_repository: CertificateOcrTextRepository,
    metadata_repository: CertificateMetadataRepository,
    activity_repository: ExtractedActivityRepository
):
    """
    Get detailed information about a specific submission.
    
    Args:
        submission_id: ID of the submission to retrieve
        
    Returns:
        JSON with detailed submission information
    """
    try:
        with get_db_session() as session:
            # Get submission
            submission = submission_repository.get_by_id(session, submission_id)
            
            if not submission:
                return jsonify({
                    'success': False,
                    'error': 'Submission not found'
                }), 404
            
            # Get related data
            student = student_repository.get_by_id(session, submission.student_id)
            ocr_text = ocr_text_repository.get_by_submission_id(session, submission.id)
            metadata = metadata_repository.get_by_submission_id(session, submission.id)
            activity = activity_repository.get_by_submission_id(session, submission.id)
            
            response_data = {
                'submission': {
                    'id': submission.id,
                    'status': submission.status,
                    'original_filename': submission.original_filename,
                    'submitted_at': submission.submitted_at.isoformat(),
                    'file_size': submission.file_size,
                    'mime_type': submission.mime_type,
                    's3_key': submission.s3_key,
                    'error_message': submission.error_message
                },
                'student': {
                    'enrollment_number': student.enrollment_number,
                    'created_at': student.created_at.isoformat()
                } if student else None,
                'ocr_text': {
                    'raw_text': ocr_text.raw_text,
                    'confidence': float(ocr_text.ocr_confidence) if ocr_text.ocr_confidence else None,
                    'extracted_at': ocr_text.extracted_at.isoformat()
                } if ocr_text else None,
                'metadata': {
                    'event_name': metadata.event_name,
                    'location': metadata.location,
                    'event_date': metadata.event_date,
                    'participant_name': metadata.participant_name,
                    'original_hours': metadata.original_hours,
                    'numeric_hours': metadata.numeric_hours,
                    'processing_time_ms': metadata.processing_time_ms,
                    'extracted_at': metadata.extracted_at.isoformat()
                } if metadata else None,
                'extracted_activity': {
                    'id': activity.id,
                    'category_name': activity.category.name if activity.category else None,
                    'category_id': activity.category_id,
                    'calculated_hours': activity.calculated_hours,
                    'final_hours': activity.final_hours,
                    'final_category_id': activity.final_category_id,
                    'llm_reasoning': activity.llm_reasoning,
                    'review_status': activity.review_status,
                    'processed_at': activity.processed_at.isoformat() if activity.processed_at else None
                } if activity else None
            }
            
            return jsonify({
                'success': True,
                'data': response_data
            })
            
    except Exception as e:
        logger.error(f"Error getting submission details: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve submission details'
        }), 500


@coordinator_bp.route('/approve/<int:submission_id>', methods=['POST'])
@inject
def approve_submission(
    submission_id: int,
    submission_repository: CertificateSubmissionRepository,
    activity_repository: ExtractedActivityRepository,
    category_repository: ActivityCategoryRepository
):
    """
    Approve a certificate submission with optional coordinator overrides.
    
    Args:
        submission_id: ID of the submission to approve
        
    Request body (optional):
        - final_hours: Override calculated hours (number)
        - final_category_id: Override category ID (number)
        - override_reason: Reason for override (required if overriding)
        
    Returns:
        JSON with approval result
    """
    try:
        # Get request data (empty body means approve without changes)
        # Handle case where no JSON is provided or no Content-Type header
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        elif request.data:
            # If there's data but not JSON, it's an error
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON or empty'
            }), 400
            
        final_hours = data.get('final_hours')
        final_category_id = data.get('final_category_id')
        override_reason = data.get('override_reason')
        
        # Validate override reason is provided if overriding
        if (final_hours is not None or final_category_id is not None) and not override_reason:
            return jsonify({
                'success': False,
                'error': 'override_reason is required when overriding hours or category'
            }), 400
        
        with get_db_session() as session:
            # Get submission
            submission = submission_repository.get_by_id(session, submission_id)
            
            if not submission:
                return jsonify({
                    'success': False,
                    'error': 'Submission not found'
                }), 404
            
            if submission.status != 'pending_review':
                return jsonify({
                    'success': False,
                    'error': f'Cannot approve submission with status: {submission.status}'
                }), 400
            
            # Get extracted activity
            activity = activity_repository.get_by_submission_id(session, submission_id)
            if not activity:
                return jsonify({
                    'success': False,
                    'error': 'No extracted activity found for this submission'
                }), 404
            
            # Validate final_hours if provided
            if final_hours is not None:
                if not isinstance(final_hours, (int, float)) or final_hours < 0:
                    return jsonify({
                        'success': False,
                        'error': 'final_hours must be a valid positive number'
                    }), 400
                final_hours = int(final_hours)
            
            # Validate final_category_id if provided
            if final_category_id is not None:
                if not isinstance(final_category_id, int):
                    return jsonify({
                        'success': False,
                        'error': 'final_category_id must be a valid integer'
                    }), 400
                
                # Check if category exists
                category = session.get(category_repository.model_class, final_category_id)
                if not category:
                    return jsonify({
                        'success': False,
                        'error': f'Category with ID {final_category_id} does not exist'
                    }), 400
            
            # Determine final values
            final_hours_value = final_hours if final_hours is not None else activity.calculated_hours
            final_category_value = final_category_id if final_category_id is not None else activity.category_id
            
            # Update extracted activity
            current_time = datetime.now(timezone.utc)
            
            # Set override fields if overriding
            activity.override_category_id = final_category_id if final_category_id is not None else None
            activity.override_hours = final_hours if final_hours is not None else None
            activity.override_reasoning = override_reason if override_reason else None
            
            # Set final approved values
            activity.final_category_id = final_category_value
            activity.final_hours = final_hours_value
            activity.review_status = 'approved'
            activity.reviewed_at = current_time
            activity.coordinator_id = 'system'  # You can enhance this to get actual coordinator ID
            
            # Update submission status (before commit)
            submission_repository.update_status(session, submission_id, 'approved')
            
            # Update student's total approved hours
            if submission.student and final_hours_value:
                current_total = submission.student.total_approved_hours or 0
                submission.student.total_approved_hours = current_total + final_hours_value
                logger.info(f"Updated student {submission.student.enrollment_number} total hours: {current_total} + {final_hours_value} = {submission.student.total_approved_hours}")
            
            session.commit()
            
            response_data = {
                'success': True,
                'message': 'Submission approved successfully',
                'submission_id': submission_id,
                'final_hours': final_hours_value,
                'final_category_id': final_category_value,
                'overrides_applied': {
                    'hours': final_hours is not None,
                    'category': final_category_id is not None,
                    'reason': override_reason
                } if override_reason else None
            }
            
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error approving submission: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to approve submission'
        }), 500


@coordinator_bp.route('/reject/<int:submission_id>', methods=['POST'])
@inject
def reject_submission(
    submission_id: int,
    submission_repository: CertificateSubmissionRepository,
    activity_repository: ExtractedActivityRepository
):
    """
    Reject a certificate submission.
    
    Args:
        submission_id: ID of the submission to reject
        
    Request body must contain:
        - reason: Reason for rejection
        
    Returns:
        JSON with rejection result
    """
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({
                'success': False,
                'error': 'Rejection reason is required'
            }), 400
        
        rejection_reason = data['reason']
        
        with get_db_session() as session:
            # Get submission
            submission = submission_repository.get_by_id(session, submission_id)
            
            if not submission:
                return jsonify({
                    'success': False,
                    'error': 'Submission not found'
                }), 404
            
            if submission.status != 'pending_review':
                return jsonify({
                    'success': False,
                    'error': f'Cannot reject submission with status: {submission.status}'
                }), 400
            
            # Reject the activity
            activity = activity_repository.get_by_submission_id(session, submission_id)
            if activity:
                activity_repository.reject_activity(
                    session, activity.id, rejection_reason
                )
            
            # Reject the submission
            submission_repository.reject_submission(
                session, submission_id, rejection_reason
            )
            
            return jsonify({
                'success': True,
                'message': 'Submission rejected successfully',
                'submission_id': submission_id,
                'reason': rejection_reason
            })
            
    except Exception as e:
        logger.error(f"Error rejecting submission: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to reject submission'
        }), 500