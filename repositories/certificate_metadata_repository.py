"""
Certificate metadata repository for database operations.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from models.certificate_metadata import CertificateMetadata


class CertificateMetadataRepository(BaseRepository[CertificateMetadata]):
    """Repository for CertificateMetadata entity operations."""
    
    def __init__(self):
        """Initialize CertificateMetadataRepository."""
        super().__init__(CertificateMetadata)
    
    def create_metadata(
        self,
        session: Session,
        submission_id: int,
        participant_name: Optional[str] = None,
        event_name: Optional[str] = None,
        location: Optional[str] = None,
        event_date: Optional[str] = None,
        original_hours: Optional[str] = None,
        numeric_hours: Optional[int] = None,
        extraction_method: str = 'llm',
        extraction_confidence: Optional[float] = None,
        processing_time_ms: Optional[int] = None
    ) -> CertificateMetadata:
        """
        Create certificate metadata record.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            nome_participante: Extracted participant name
            participant_name: Extracted participant name
            event_name: Extracted event/course name
            location: Extracted location/institution
            event_date: Extracted date
            original_hours: Original hour load text
            numeric_hours: Numeric hour load
            extraction_method: Method used for extraction (default: 'llm')
            extraction_confidence: Confidence score for extraction
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            Created metadata instance
        """
        metadata = CertificateMetadata(
            submission_id=submission_id,
            participant_name=participant_name,
            event_name=event_name,
            location=location,
            event_date=event_date,
            original_hours=original_hours,
            numeric_hours=numeric_hours,
            extraction_method=extraction_method,
            extraction_confidence=extraction_confidence,
            processing_time_ms=processing_time_ms,
            extracted_at=datetime.now(timezone.utc)
        )
        session.add(metadata)
        session.flush()
        return metadata
    
    def get_by_submission_id(
        self, 
        session: Session, 
        submission_id: int
    ) -> Optional[CertificateMetadata]:
        """
        Get metadata by submission ID.
        
        Args:
            session: Database session
            submission_id: Certificate submission ID
            
        Returns:
            Metadata instance or None if not found
        """
        return session.query(CertificateMetadata).filter_by(
            submission_id=submission_id
        ).first()
    
    def update_metadata(
        self,
        session: Session,
        metadata_id: int,
        **updates
    ) -> Optional[CertificateMetadata]:
        """
        Update metadata fields.
        
        Args:
            session: Database session
            metadata_id: Metadata ID
            **updates: Fields to update
            
        Returns:
            Updated metadata instance or None if not found
        """
        metadata = self.get_by_id(session, metadata_id)
        
        if metadata:
            for key, value in updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            session.flush()
        
        return metadata