"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config.settings as settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Import all models to ensure they are registered with Base
# This must be done after Base is created but before any table operations
try:
    from models import (
        Student, CertificateSubmission, CertificateOcrText,
        CertificateMetadata, ExtractedActivity
    )
except ImportError:
    # Models may not be available during initial setup
    pass


def Session():
    """Create a new database session."""
    return SessionLocal()


def get_db_session():
    """Get database session with context manager support."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()