"""
Certificate metadata model for storing LLM extracted information.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class CertificateMetadata(Base):
    """Model for storing LLM extracted metadata."""
    __tablename__ = 'certificate_metadata'
    
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey('certificate_submissions.id'))
    
    # LLM extracted fields (English column names)
    participant_name = Column(String(500))
    event_name = Column(String(1000))
    location = Column(String(500))
    event_date = Column(String(200))
    original_hours = Column(String(100))
    numeric_hours = Column(Integer)
    
    # Extraction metadata
    extraction_method = Column(String(50), default='llm')
    extraction_confidence = Column(DECIMAL(5, 2))
    processing_time_ms = Column(Integer)
    extracted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    submission = relationship('CertificateSubmission', back_populates='certificate_metadata')
    
    def __repr__(self):
        return f'<CertificateMetadata {self.id}: {self.event_name}>'
    
    def to_dict(self):
        """Convert metadata to dictionary for API responses."""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'participant_name': self.participant_name,
            'event_name': self.event_name,
            'location': self.location,
            'event_date': self.event_date,
            'original_hours': self.original_hours,
            'numeric_hours': self.numeric_hours,
            'extraction_method': self.extraction_method,
            'extraction_confidence': float(self.extraction_confidence) if self.extraction_confidence else None,
            'processing_time_ms': self.processing_time_ms,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }