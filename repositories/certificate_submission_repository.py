"""
Certificate submission repository for database operations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from repositories.base_repository import BaseRepository
from models.certificate_submission import CertificateSubmission
from models.student import Student


class CertificateSubmissionRepository(BaseRepository[CertificateSubmission]):
    """Repository for CertificateSubmission entity operations."""
    
    def __init__(self):
        """Initialize CertificateSubmissionRepository."""
        super().__init__(CertificateSubmission)
    
    def create_submission(
        self,
        session: Session,
        student_id: int,
        original_filename: str,
        s3_key: str,
        file_checksum: str,
        file_size: int,
        mime_type: str,
        status: str = 'uploaded'
    ) -> CertificateSubmission:
        """
        Create a new certificate submission.
        
        Args:
            session: Database session
            student_id: Student ID
            original_filename: Original filename
            s3_key: S3 storage key
            file_checksum: File checksum for duplicate detection
            file_size: File size in bytes
            mime_type: File MIME type
            status: Initial status
            
        Returns:
            Created submission instance
        """
        submission = CertificateSubmission(
            student_id=student_id,
            original_filename=original_filename,
            s3_key=s3_key,
            file_checksum=file_checksum,
            file_size=file_size,
            mime_type=mime_type,
            status=status,
            submitted_at=datetime.now(timezone.utc)
        )
        session.add(submission)
        session.flush()
        return submission
    
    def get_by_checksum(
        self, 
        session: Session, 
        student_id: int,
        file_checksum: str
    ) -> Optional[CertificateSubmission]:
        """
        Get submission by student ID and file checksum (for duplicate detection).
        
        Args:
            session: Database session
            student_id: Student ID
            file_checksum: File checksum
            
        Returns:
            Submission instance or None if not found
        """
        return session.query(CertificateSubmission).filter(
            and_(
                CertificateSubmission.student_id == student_id,
                CertificateSubmission.file_checksum == file_checksum
            )
        ).first()
    
    def get_by_student_id(
        self,
        session: Session,
        student_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CertificateSubmission]:
        """
        Get submissions by student ID with optional status filter.
        
        Args:
            session: Database session
            student_id: Student ID
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of submission instances
        """
        query = session.query(CertificateSubmission).filter_by(
            student_id=student_id
        )
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(
            CertificateSubmission.submitted_at.desc()
        ).offset(offset).limit(limit).all()
    
    def update_status(
        self,
        session: Session,
        submission_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[CertificateSubmission]:
        """
        Update submission status and optional error message.
        
        Args:
            session: Database session
            submission_id: Submission ID
            status: New status
            error_message: Optional error message
            
        Returns:
            Updated submission instance or None if not found
        """
        submission = self.get_by_id(session, submission_id)
        
        if submission:
            submission.status = status
            if error_message:
                submission.error_message = error_message
            session.flush()
        
        return submission
    
    def get_pending_submissions(
        self,
        session: Session,
        status: str = 'pending_review',
        enrollment_filter: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[List[CertificateSubmission], int]:
        """
        Get pending submissions with pagination and optional filters.
        
        Args:
            session: Database session
            status: Status filter
            enrollment_filter: Optional enrollment number filter
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Tuple of (submissions list, total count)
        """
        query = session.query(CertificateSubmission).filter_by(status=status)
        
        if enrollment_filter:
            query = query.join(Student).filter(
                Student.enrollment_number.ilike(f'%{enrollment_filter}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        submissions = query.order_by(
            CertificateSubmission.submitted_at.desc()
        ).offset(offset).limit(per_page).all()
        
        return submissions, total
    
    def get_submission_with_details(
        self,
        session: Session,
        submission_id: int
    ) -> Optional[CertificateSubmission]:
        """
        Get submission with all related details (student, OCR, metadata, activity).
        
        Args:
            session: Database session
            submission_id: Submission ID
            
        Returns:
            Submission instance with eager-loaded relationships or None
        """
        from models.certificate_ocr_text import CertificateOcrText
        from models.certificate_metadata import CertificateMetadata
        from models.extracted_activity import ExtractedActivity
        
        return session.query(CertificateSubmission).filter_by(
            id=submission_id
        ).first()
    
    def approve_submission(
        self,
        session: Session,
        submission_id: int,
        approved_by: Optional[str] = None
    ) -> Optional[CertificateSubmission]:
        """
        Approve a submission.
        
        Args:
            session: Database session
            submission_id: Submission ID
            approved_by: Optional identifier of who approved
            
        Returns:
            Updated submission instance or None if not found
        """
        submission = self.get_by_id(session, submission_id)
        
        if submission:
            submission.status = 'approved'
            submission.approved_at = datetime.now(timezone.utc)
            if approved_by:
                submission.approved_by = approved_by
            session.flush()
        
        return submission
    
    def reject_submission(
        self,
        session: Session,
        submission_id: int,
        rejection_reason: str,
        rejected_by: Optional[str] = None
    ) -> Optional[CertificateSubmission]:
        """
        Reject a submission.
        
        Args:
            session: Database session
            submission_id: Submission ID
            rejection_reason: Reason for rejection
            rejected_by: Optional identifier of who rejected
            
        Returns:
            Updated submission instance or None if not found
        """
        submission = self.get_by_id(session, submission_id)
        
        if submission:
            submission.status = 'rejected'
            submission.rejected_at = datetime.now(timezone.utc)
            submission.rejection_reason = rejection_reason
            if rejected_by:
                submission.rejected_by = rejected_by
            session.flush()
        
        return submission