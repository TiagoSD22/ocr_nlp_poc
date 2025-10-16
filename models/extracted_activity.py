"""
Extracted activity model for activity categorization and coordinator review.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class ExtractedActivity(Base):
    """Model for storing extracted and processed activity data with coordinator review."""
    __tablename__ = 'extracted_activities'
    
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey('certificate_submissions.id'))
    metadata_id = Column(Integer, ForeignKey('certificate_metadata.id'))
    student_id = Column(Integer, ForeignKey('students.id'))
    enrollment_number = Column(String(50))
    filename = Column(String(500))
    
    # Extracted certificate data (English field names)
    participant_name = Column(String(500))
    event_name = Column(String(1000))
    location = Column(String(500))
    event_date = Column(String(200))
    original_hours = Column(String(100))
    numeric_hours = Column(Integer)
    
    # LLM categorization results
    category_id = Column(Integer, ForeignKey('activity_categories.id'))
    calculated_hours = Column(Integer)
    llm_reasoning = Column(Text)
    raw_text = Column(Text)
    
    # Review workflow fields
    review_status = Column(String(50), default='pending_review')  # 'pending_review', 'approved', 'rejected', 'manual_override'
    coordinator_id = Column(String(100))  # ID of coordinator who reviewed
    coordinator_comments = Column(Text)
    reviewed_at = Column(DateTime)
    
    # Manual override fields (when coordinator disagrees with LLM)
    override_category_id = Column(Integer, ForeignKey('activity_categories.id'))
    override_hours = Column(Integer)
    override_reasoning = Column(Text)
    
    # Final approved values (either LLM or override)
    final_category_id = Column(Integer, ForeignKey('activity_categories.id'))
    final_hours = Column(Integer)
    
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    submission = relationship('CertificateSubmission', back_populates='activities')
    certificate_metadata = relationship('CertificateMetadata')
    student = relationship('Student')
    category = relationship('ActivityCategory', foreign_keys='ExtractedActivity.category_id')
    override_category = relationship('ActivityCategory', foreign_keys='ExtractedActivity.override_category_id')
    final_category = relationship('ActivityCategory', foreign_keys='ExtractedActivity.final_category_id')
    
    def __repr__(self):
        return f'<ExtractedActivity {self.id}: {self.event_name}>'
    
    def to_dict(self):
        """Convert activity to dictionary for API responses."""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'metadata_id': self.metadata_id,
            'student_id': self.student_id,
            'enrollment_number': self.enrollment_number,
            'filename': self.filename,
            'participant_name': self.participant_name,
            'event_name': self.event_name,
            'location': self.location,
            'event_date': self.event_date,
            'original_hours': self.original_hours,
            'numeric_hours': self.numeric_hours,
            'category_id': self.category_id,
            'calculated_hours': self.calculated_hours,
            'llm_reasoning': self.llm_reasoning,
            'raw_text': self.raw_text,
            'review_status': self.review_status,
            'coordinator_id': self.coordinator_id,
            'coordinator_comments': self.coordinator_comments,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'override_category_id': self.override_category_id,
            'override_hours': self.override_hours,
            'override_reasoning': self.override_reasoning,
            'final_category_id': self.final_category_id,
            'final_hours': self.final_hours,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }