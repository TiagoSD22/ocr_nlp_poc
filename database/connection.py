"""
Database connection and session management.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import config.settings as settings

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL logging in development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Provides automatic session management with proper cleanup and error handling.
    
    Usage:
        with get_db_session() as session:
            # Use session here
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_session() -> Session:
    """
    Get a new database session.
    
    Note: Remember to close the session when done.
    Consider using get_db_session() context manager instead.
    
    Returns:
        SQLAlchemy session instance
    """
    return SessionLocal()


def init_database():
    """
    Initialize database tables.
    
    This should be called during application startup.
    Models are already imported in database/__init__.py
    """
    try:
        from database import Base
        
        # Check if we can connect to the database first
        with engine.connect() as conn:
            logger.info("Database connection established")
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database tables initialized successfully")
        
    except Exception as e:
        logger.warning(f"Database initialization encountered an issue: {e}")
        # Don't raise the exception - tables might already exist
        # This allows the application to continue if tables are already created
        logger.info("Continuing with existing database schema")


def health_check() -> bool:
    """
    Check database connectivity.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with get_db_session() as session:
            session.execute('SELECT 1')
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False