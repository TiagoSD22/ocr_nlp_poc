"""
Certificate submission model for tracking async processing pipeline.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class CertificateSubmission(Base):
    """Model for tracking certificate submissions through async pipeline."""
    __tablename__ = 'certificate_submissions'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    original_filename = Column(String(500))
    s3_key = Column(String(1000), nullable=False)
    file_checksum = Column(String(64), unique=True, nullable=False)  # SHA-256
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    status = Column(String(50), default='uploaded')  # uploaded, queued, ocr_processing, etc.
    error_message = Column(String(1000))
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Relationships
    student = relationship('Student', back_populates='submissions')
    ocr_text = relationship('CertificateOcrText', back_populates='submission', uselist=False)
    certificate_metadata = relationship('CertificateMetadata', back_populates='submission')
    activities = relationship('ExtractedActivity', back_populates='submission')
    
    def __repr__(self):
        return f'<CertificateSubmission {self.id}: {self.original_filename}>'
    
    def to_dict(self):
        """Convert submission to dictionary for API responses."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'original_filename': self.original_filename,
            's3_key': self.s3_key,
            'file_checksum': self.file_checksum,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'status': self.status,
            'error_message': self.error_message,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None
        }