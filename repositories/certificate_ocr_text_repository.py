"""
Certificate OCR text repository for database operations.
"""
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from models.certificate_ocr_text import CertificateOcrText


class CertificateOcrTextRepository(BaseRepository[CertificateOcrText]):
    """Repository for CertificateOcrText entity operations."""
    
    def __init__(self):
        """Initialize CertificateOcrTextRepository."""
        super().__init__(CertificateOcrText)
    
    def create_ocr_text(
        self,
        session: Session,
        submission_id: int,
        raw_text: str,
        ocr_confidence: Optional[float] = None
    ) -> CertificateOcrText:
        """
        Create OCR text record.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            raw_text: Extracted OCR text
            ocr_confidence: OCR confidence score
            
        Returns:
            Created OCR text instance
        """
        ocr_text = CertificateOcrText(
            submission_id=submission_id,
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            extracted_at=datetime.now(timezone.utc)
        )
        session.add(ocr_text)
        session.flush()
        return ocr_text
    
    def get_by_submission_id(
        self, 
        session: Session, 
        submission_id: int
    ) -> Optional[CertificateOcrText]:
        """
        Get OCR text by submission ID.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            
        Returns:
            OCR text instance or None if not found
        """
        return session.query(CertificateOcrText).filter_by(
            submission_id=submission_id
        ).first()