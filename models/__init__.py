"""
Database models package.
"""
# Import all models for easy access
from .student import Student
from .certificate_submission import CertificateSubmission
from .certificate_ocr_text import CertificateOcrText
from .certificate_metadata import CertificateMetadata
from .extracted_activity import ExtractedActivity
from .activity_category import ActivityCategory

# Import Base for table creation
from database import Base
from database.connection import SessionLocal as db

# Export all models
__all__ = [
    'Student',
    'CertificateSubmission', 
    'CertificateOcrText',
    'CertificateMetadata',
    'ExtractedActivity',
    'ActivityCategory',
    'Base',
    'db'
    'Base'
]