"""
OCR text model for storing extracted text results.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class CertificateOcrText(Base):
    """Model for storing OCR extracted text for audit purposes."""
    __tablename__ = 'certificate_ocr_texts'
    
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey('certificate_submissions.id'))
    raw_text = Column(Text, nullable=False)
    ocr_confidence = Column(DECIMAL(5, 2))
    extracted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    submission = relationship('CertificateSubmission', back_populates='ocr_text')
    
    def __repr__(self):
        return f'<CertificateOcrText {self.id}: {len(self.raw_text)} chars>'
    
    def to_dict(self):
        """Convert OCR text to dictionary for API responses."""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'raw_text': self.raw_text,
            'ocr_confidence': float(self.ocr_confidence) if self.ocr_confidence else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }