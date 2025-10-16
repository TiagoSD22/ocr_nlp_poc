"""
Activity category model for storing predefined certificate activity categories.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class ActivityCategory(Base):
    """Model for activity categories used in certificate classification."""
    __tablename__ = 'activity_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    calculation_type = Column(String(50), nullable=False)  # 'fixed_per_semester', 'fixed_per_activity', 'ratio_hours', etc.
    hours_awarded = Column(Integer)  # Hours awarded per unit (for fixed calculations)
    input_unit = Column(String(50))  # What unit is being measured: 'hours', 'days', 'pages', 'activities', 'semesters'
    input_quantity = Column(Integer)  # How many input units are needed
    output_hours = Column(Integer)  # How many hours are awarded for that input quantity
    max_total_hours = Column(Integer)  # Maximum hours student can have in this category
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    activities = relationship('ExtractedActivity', foreign_keys='ExtractedActivity.category_id', back_populates='category')
    override_activities = relationship('ExtractedActivity', foreign_keys='ExtractedActivity.override_category_id')
    final_activities = relationship('ExtractedActivity', foreign_keys='ExtractedActivity.final_category_id')
    
    def __repr__(self):
        return f'<ActivityCategory {self.id}: {self.name}>'
    
    def to_dict(self):
        """Convert activity category to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'calculation_type': self.calculation_type,
            'hours_awarded': self.hours_awarded,
            'input_unit': self.input_unit,
            'input_quantity': self.input_quantity,
            'output_hours': self.output_hours,
            'max_total_hours': self.max_total_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }