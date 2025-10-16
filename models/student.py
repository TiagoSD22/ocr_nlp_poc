"""
Student model for managing student information.
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Student(Base):
    """Model for student information."""
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    enrollment_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    email = Column(String(255))
    total_approved_hours = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    submissions = relationship('CertificateSubmission', back_populates='student')
    
    def __repr__(self):
        return f'<Student {self.enrollment_number}: {self.name}>'
    
    def to_dict(self):
        """Convert student to dictionary for API responses."""
        return {
            'id': self.id,
            'enrollment_number': self.enrollment_number,
            'name': self.name,
            'email': self.email,
            'total_approved_hours': self.total_approved_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }