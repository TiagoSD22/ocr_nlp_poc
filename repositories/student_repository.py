"""
Student repository for database operations.
"""
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from models.student import Student


class StudentRepository(BaseRepository[Student]):
    """Repository for Student entity operations."""
    
    def __init__(self):
        """Initialize StudentRepository."""
        super().__init__(Student)
    
    def get_by_enrollment_number(
        self, 
        session: Session, 
        enrollment_number: str
    ) -> Optional[Student]:
        """
        Get student by enrollment number.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            
        Returns:
            Student instance or None if not found
        """
        return session.query(Student).filter_by(
            enrollment_number=enrollment_number
        ).first()
    
    def create_student(
        self, 
        session: Session, 
        enrollment_number: str
    ) -> Student:
        """
        Create a new student.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            
        Returns:
            Created student instance
        """
        student = Student(
            enrollment_number=enrollment_number,
            created_at=datetime.now(timezone.utc)
        )
        session.add(student)
        session.flush()  # Get the ID without committing
        return student
    
    def get_or_create_student(
        self, 
        session: Session, 
        enrollment_number: str
    ) -> Student:
        """
        Get existing student or create new one.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            
        Returns:
            Student instance (existing or newly created)
        """
        student = self.get_by_enrollment_number(session, enrollment_number)
        
        if not student:
            student = self.create_student(session, enrollment_number)
        
        return student
    
    def exists_by_enrollment_number(
        self, 
        session: Session, 
        enrollment_number: str
    ) -> bool:
        """
        Check if student exists by enrollment number.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            
        Returns:
            True if student exists, False otherwise
        """
        return self.exists(session, enrollment_number=enrollment_number)