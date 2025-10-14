"""
Database models for activity categorization.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()


class ActivityCategory(db.Model):
    """Model for activity categories with calculation rules."""
    __tablename__ = 'activity_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    calculation_type = Column(String(50), nullable=False)  # 'fixed_per_semester', 'fixed_per_activity', 'ratio_hours', 'ratio_days', 'ratio_pages'
    hours_awarded = Column(Integer)  # Hours awarded per unit (for fixed calculations)
    input_unit = Column(String(50))  # What unit is being measured: 'hours', 'days', 'pages', 'activities', 'semesters'
    input_quantity = Column(Integer)  # How many input units are needed
    output_hours = Column(Integer)  # How many hours are awarded for that input quantity
    max_total_hours = Column(Integer)  # Maximum hours student can have in this category
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    extracted_activities = relationship('ExtractedActivity', back_populates='category')
    
    def __repr__(self):
        return f'<ActivityCategory {self.name}>'


class ExtractedActivity(db.Model):
    """Model for storing extracted and processed activity data."""
    __tablename__ = 'extracted_activities'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(500))
    nome_participante = Column(String(500))
    evento = Column(String(1000))
    local = Column(String(500))
    data = Column(String(200))
    carga_horaria_original = Column(String(100))
    carga_horaria_numeric = Column(Integer)
    category_id = Column(Integer, ForeignKey('activity_categories.id'))
    calculated_hours = Column(Integer)
    llm_reasoning = Column(Text)  # Store LLM's reasoning for category selection
    raw_text = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship('ActivityCategory', back_populates='extracted_activities')
    
    def __repr__(self):
        return f'<ExtractedActivity {self.evento}>'