"""
Extracted activity repository for database operations.
"""
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from models.extracted_activity import ExtractedActivity


class ExtractedActivityRepository(BaseRepository[ExtractedActivity]):
    """Repository for ExtractedActivity entity operations."""
    
    def __init__(self):
        """Initialize ExtractedActivityRepository."""
        super().__init__(ExtractedActivity)
    
    def create_activity(
        self,
        session: Session,
        submission_id: int,
        metadata_id: Optional[int] = None,
        student_id: Optional[int] = None,
        enrollment_number: Optional[str] = None,
        filename: Optional[str] = None,
        participant_name: Optional[str] = None,
        event_name: Optional[str] = None,
        location: Optional[str] = None,
        event_date: Optional[str] = None,
        original_hours: Optional[str] = None,
        numeric_hours: Optional[int] = None,
        category_id: Optional[int] = None,
        calculated_hours: Optional[int] = None,
        llm_reasoning: Optional[str] = None,
        raw_text: Optional[str] = None,
        review_status: str = 'pending_review'
    ) -> ExtractedActivity:
        """
        Create extracted activity record.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            metadata_id: Related metadata record ID
            student_id: Student ID
            enrollment_number: Student enrollment number
            filename: Original filename
            participant_name: Extracted participant name
            event_name: Extracted event name
            location: Extracted location
            event_date: Extracted event date
            original_hours: Original hours text
            numeric_hours: Numeric hours value
            category_id: Categorized activity category ID
            calculated_hours: LLM calculated hours
            llm_reasoning: LLM reasoning for categorization
            raw_text: Original OCR text
            review_status: Activity status
            
        Returns:
            Created activity instance
        """
        activity = ExtractedActivity(
            submission_id=submission_id,
            metadata_id=metadata_id,
            student_id=student_id,
            enrollment_number=enrollment_number,
            filename=filename,
            participant_name=participant_name,
            event_name=event_name,
            location=location,
            event_date=event_date,
            original_hours=original_hours,
            numeric_hours=numeric_hours,
            category_id=category_id,
            calculated_hours=calculated_hours,
            llm_reasoning=llm_reasoning,
            raw_text=raw_text,
            review_status=review_status,
            processed_at=datetime.now(timezone.utc)
        )
        session.add(activity)
        session.flush()
        return activity
    
    def get_by_submission_id(
        self, 
        session: Session, 
        submission_id: int
    ) -> Optional[ExtractedActivity]:
        """
        Get activity by submission ID.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            
        Returns:
            Activity instance or None if not found
        """
        return session.query(ExtractedActivity).filter_by(
            submission_id=submission_id
        ).first()
    
    def approve_activity(
        self,
        session: Session,
        activity_id: int,
        final_hours: Optional[int] = None,
        final_category_id: Optional[int] = None
    ) -> Optional[ExtractedActivity]:
        """
        Approve an activity with optional overrides.
        
        Args:
            session: Database session
            activity_id: Activity ID
            final_hours: Final approved hours (overrides calculated)
            final_category_id: Final category ID (overrides categorized)
            
        Returns:
            Updated activity instance or None if not found
        """
        activity = self.get_by_id(session, activity_id)
        
        if activity:
            activity.status = 'approved'
            activity.approved_at = datetime.now(timezone.utc)
            
            if final_hours is not None:
                activity.final_hours = final_hours
            else:
                activity.final_hours = activity.calculated_hours
                
            if final_category_id is not None:
                activity.final_category_id = final_category_id
            else:
                activity.final_category_id = activity.category_id
                
            session.flush()
        
        return activity
    
    def reject_activity(
        self,
        session: Session,
        activity_id: int,
        rejection_reason: str
    ) -> Optional[ExtractedActivity]:
        """
        Reject an activity.
        
        Args:
            session: Database session
            activity_id: Activity ID
            rejection_reason: Reason for rejection
            
        Returns:
            Updated activity instance or None if not found
        """
        activity = self.get_by_id(session, activity_id)
        
        if activity:
            activity.status = 'rejected'
            activity.rejected_at = datetime.now(timezone.utc)
            activity.rejection_reason = rejection_reason
            session.flush()
        
        return activity