"""
Certificate Submission Service for handling async certificate processing workflow.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from injector import inject

from database.connection import get_db_session
from services.student_service import StudentService
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from services.s3_service import S3Service
from services.kafka_service import KafkaService

logger = logging.getLogger(__name__)


class CertificateSubmissionService:
    """Service for handling certificate submission operations."""
    
    @inject
    def __init__(
        self, 
        s3_service: S3Service, 
        kafka_service: KafkaService,
        student_service: StudentService,
        submission_repository: CertificateSubmissionRepository
    ):
        """Initialize certificate submission service."""
        self.s3_service = s3_service
        self.kafka_service = kafka_service
        self.student_service = student_service
        self.submission_repository = submission_repository
    
    def submit_certificate(
        self, 
        file_content: bytes,
        original_filename: str,
        enrollment_number: str,
        mime_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit certificate for async processing.
        
        Args:
            file_content: Binary content of the uploaded file
            original_filename: Original filename of the uploaded file
            enrollment_number: Student enrollment number
            mime_type: MIME type of the file
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Calculate file checksum for duplicate detection
            checksum = self.s3_service.calculate_checksum(file_content)
            
            with get_db_session() as session:
                # Validate student exists (don't create new students)
                student = self.student_service.get_student_for_certificate_submission(
                    session, enrollment_number
                )
                
                if not student:
                    return False, {
                        'error': 'Student not found or invalid',
                        'details': f'No valid student found with enrollment number: {enrollment_number}',
                        'solution': 'Please register the student first using the /api/v1/student/register endpoint'
                    }
                
                # Check for duplicate submission
                duplicate_submission = self.submission_repository.get_by_checksum(
                    session, student.id, checksum
                )
                if duplicate_submission:
                    return False, {
                        'error': 'Duplicate file detected',
                        'details': 'This file has already been submitted',
                        'existing_submission_id': duplicate_submission.id,
                        'existing_submission_date': duplicate_submission.submitted_at.isoformat()
                    }
                
                # Upload file to S3
                s3_result = self.s3_service.upload_file(
                    file_content=file_content,
                    enrollment_number=enrollment_number,
                    filename=original_filename,
                    checksum=checksum
                )
                
                if not s3_result.get('success'):
                    return False, {'error': 'Failed to upload file to storage'}
                
                s3_key = s3_result['s3_key']
                
                # Create submission record
                submission = self.submission_repository.create_submission(
                    session=session,
                    student_id=student.id,
                    original_filename=original_filename,
                    s3_key=s3_key,
                    file_checksum=checksum,
                    file_size=len(file_content),
                    mime_type=mime_type,
                    status='uploaded'
                )
                
                # Update submission status to queued
                self.submission_repository.update_status(
                    session, submission.id, 'queued'
                )
                
                # Store submission data for Kafka publishing after commit
                submission_data = {
                    'submission_id': submission.id,
                    'enrollment_number': enrollment_number,
                    's3_key': s3_key,
                    'checksum': checksum,
                    'original_filename': original_filename,
                    'file_size': len(file_content),
                    'submitted_at': submission.submitted_at.isoformat()
                }
                
            # Database transaction committed here - now safe to publish to Kafka
            
            # Publish to Kafka for async processing
            kafka_success = self.kafka_service.publish_certificate_ingest(
                submission_id=submission_data['submission_id'],
                enrollment_number=submission_data['enrollment_number'],
                s3_key=submission_data['s3_key'],
                checksum=submission_data['checksum'],
                original_filename=submission_data['original_filename']
            )
            
            if not kafka_success:
                # If Kafka publishing fails, update submission status
                with get_db_session() as session:
                    self.submission_repository.update_status(
                        session, 
                        submission_data['submission_id'], 
                        'failed',
                        'Failed to publish to processing queue'
                    )
                
                return False, {
                    'error': 'Failed to queue file for processing',
                    'submission_id': submission_data['submission_id']
                }
            
            # Return success response
            return True, {
                'submission_id': submission_data['submission_id'],
                'enrollment_number': submission_data['enrollment_number'],
                'filename': submission_data['original_filename'],
                'file_size': submission_data['file_size'],
                'status': 'queued',
                'submitted_at': submission_data['submitted_at'],
                'checksum': submission_data['checksum'][:8] + '...'  # First 8 chars for identification
            }
                
        except Exception as e:
            logger.error(f"Error submitting certificate: {e}")
            return False, {'error': f'Submission failed: {str(e)}'}
    
    def get_submission_status(self, submission_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get submission status and details.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            with get_db_session() as session:
                submission = self.submission_repository.get_by_id(
                    session, submission_id
                )
                
                if not submission:
                    return False, {'error': 'Submission not found'}
                
                response_data = {
                    'submission_id': submission.id,
                    'enrollment_number': submission.student.enrollment_number if submission.student else None,
                    'original_filename': submission.original_filename,
                    'status': submission.status,
                    'submitted_at': submission.submitted_at.isoformat(),
                    'file_size': submission.file_size,
                    'mime_type': submission.mime_type
                }
                
                # Add presigned URL for file download
                self._add_presigned_url_to_submission(response_data, submission)
                
                # Add error message if present
                if submission.error_message:
                    response_data['error_message'] = submission.error_message
                
                return True, response_data
                
        except Exception as e:
            logger.error(f"Error getting submission status: {e}")
            return False, {'error': f'Database error: {str(e)}'}
    
    def get_student_submissions(
        self, 
        enrollment_number: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get submissions for a specific student.
        
        Args:
            enrollment_number: Student enrollment number
            status: Optional status filter
            limit: Maximum number of submissions to return
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            with get_db_session() as session:
                # Get student
                student = self.student_service.get_student_by_enrollment(
                    session, enrollment_number
                )
                
                if not student:
                    return False, {'error': 'Student not found'}
                
                # Get submissions
                submissions = self.submission_repository.get_by_student_id(
                    session, student.id, status, limit
                )
                
                # Format response
                submission_list = []
                for submission in submissions:
                    submission_data = {
                        'submission_id': submission.id,
                        'original_filename': submission.original_filename,
                        'status': submission.status,
                        'submitted_at': submission.submitted_at.isoformat(),
                        'file_size': submission.file_size,
                        'mime_type': submission.mime_type
                    }
                    
                    # Add presigned URL for file download
                    self._add_presigned_url_to_submission(submission_data, submission)
                    
                    # Add error message if present
                    if submission.error_message:
                        submission_data['error_message'] = submission.error_message
                    
                    submission_list.append(submission_data)
                
                return True, {
                    'enrollment_number': enrollment_number,
                    'total_submissions': len(submission_list),
                    'submissions': submission_list
                }
                
        except Exception as e:
            logger.error(f"Error getting student submissions: {e}")
            return False, {'error': f'Error retrieving submissions: {str(e)}'}
    
    def _add_presigned_url_to_submission(self, submission_data: Dict[str, Any], submission) -> None:
        """
        Add presigned URL to submission data if S3 key exists.
        
        Args:
            submission_data: Dictionary to add the download URL to
            submission: Submission object with s3_key attribute
        """
        if submission.s3_key:
            try:
                presigned_url = self.s3_service.generate_presigned_url(submission.s3_key)
                submission_data['download_url'] = presigned_url
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for submission {submission.id}: {e}")
                submission_data['download_url'] = None
        else:
            submission_data['download_url'] = None