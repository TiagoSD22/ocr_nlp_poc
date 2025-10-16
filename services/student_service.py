"""
Student service for business logic operations.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.student_repository import StudentRepository
from models.student import Student

logger = logging.getLogger(__name__)


class StudentService:
    """Service class for student-related business operations."""
    
    def __init__(self):
        """Initialize StudentService."""
        self.student_repository = StudentRepository()
    
    def register_student(
        self, 
        session: Session, 
        enrollment_number: str, 
        name: str, 
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new student in the system.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number (unique)
            name: Student full name
            email: Student email address (optional)
            
        Returns:
            Dictionary with student information and success status
            
        Raises:
            ValueError: If student already exists or validation fails
        """
        # Validate inputs
        if not enrollment_number or not enrollment_number.strip():
            raise ValueError("Enrollment number is required")
        
        if not name or not name.strip():
            raise ValueError("Name is required")
        
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        
        enrollment_number = enrollment_number.strip()
        name = name.strip()
        email = email.strip() if email else None
        
        # Check if student already exists
        existing_student = self.student_repository.get_by_enrollment_number(
            session, enrollment_number
        )
        if existing_student:
            raise ValueError(f"Student with enrollment number {enrollment_number} already exists")
        
        # Create new student
        student = self.student_repository.create(
            session,
            enrollment_number=enrollment_number,
            name=name,
            email=email,
            created_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Student registered successfully: {student.enrollment_number}")
        
        return {
            'success': True,
            'message': 'Student registered successfully',
            'student': student.to_dict()
        }
    
    def get_student_by_enrollment(
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
        if not enrollment_number or not enrollment_number.strip():
            return None
        
        return self.student_repository.get_by_enrollment_number(
            session, enrollment_number.strip()
        )
    
    def update_student(
        self,
        session: Session,
        enrollment_number: str,
        **update_data
    ) -> Dict[str, Any]:
        """
        Update student information.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            **update_data: Fields to update
            
        Returns:
            Dictionary with updated student information
            
        Raises:
            ValueError: If student not found or validation fails
        """
        if not enrollment_number or not enrollment_number.strip():
            raise ValueError("Enrollment number is required")
        
        student = self.student_repository.get_by_enrollment_number(
            session, enrollment_number.strip()
        )
        
        if not student:
            raise ValueError(f"Student with enrollment number {enrollment_number} not found")
        
        # Validate and clean update data
        clean_update_data = {}
        
        if 'name' in update_data:
            name = update_data['name']
            if name and name.strip():
                clean_update_data['name'] = name.strip()
            else:
                raise ValueError("Name cannot be empty")
        
        if 'email' in update_data:
            email = update_data['email']
            if email:
                email = email.strip()
                if '@' not in email:
                    raise ValueError("Invalid email format")
                clean_update_data['email'] = email
            else:
                clean_update_data['email'] = None
        
        if not clean_update_data:
            raise ValueError("No valid fields to update")
        
        # Add updated timestamp
        clean_update_data['updated_at'] = datetime.now(timezone.utc)
        
        # Update student
        updated_student = self.student_repository.update(
            session, student, **clean_update_data
        )
        
        logger.info(f"Student updated successfully: {updated_student.enrollment_number}")
        
        return {
            'success': True,
            'message': 'Student updated successfully',
            'student': updated_student.to_dict()
        }
    
    def student_exists(
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
        if not enrollment_number or not enrollment_number.strip():
            return False
        
        return self.student_repository.exists_by_enrollment_number(
            session, enrollment_number.strip()
        )
    
    def get_student_for_certificate_submission(
        self, 
        session: Session, 
        enrollment_number: str
    ) -> Optional[Student]:
        """
        Get student for certificate submission validation.
        This method is specifically for certificate submission workflow.
        
        Args:
            session: Database session
            enrollment_number: Student enrollment number
            
        Returns:
            Student instance if found and valid, None otherwise
        """
        student = self.get_student_by_enrollment(session, enrollment_number)
        
        if not student:
            logger.warning(f"Student not found for certificate submission: {enrollment_number}")
            return None
        
        if not student.name:
            logger.warning(f"Student found but missing required name field: {enrollment_number}")
            return None
        
        return student