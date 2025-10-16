"""
Repository for ActivityCategory database operations.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models.activity_category import ActivityCategory
from .base_repository import BaseRepository


class ActivityCategoryRepository(BaseRepository[ActivityCategory]):
    """Repository for activity category operations."""
    
    def __init__(self):
        """Initialize repository with ActivityCategory model."""
        super().__init__(ActivityCategory)
    
    def get_all_categories(self, session: Session) -> List[ActivityCategory]:
        """
        Get all activity categories.
        
        Args:
            session: Database session
            
        Returns:
            List of all activity categories
        """
        return session.query(self.model_class).all()
    
    def get_categories_dict(self, session: Session) -> Dict[int, Dict[str, any]]:
        """
        Get all categories as a dictionary with category data.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary mapping category ID to category data
        """
        categories = self.get_all_categories(session)
        categories_dict = {}
        
        for category in categories:
            categories_dict[category.id] = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'calculation_type': category.calculation_type,
                'hours_awarded': category.hours_awarded,
                'input_unit': category.input_unit,
                'input_quantity': category.input_quantity,
                'output_hours': category.output_hours,
                'max_total_hours': category.max_total_hours
            }
        
        return categories_dict
    
    def get_categories_formatted_text(self, session: Session) -> str:
        """
        Get formatted text of available activity categories for LLM prompt.
        
        Args:
            session: Database session
            
        Returns:
            Formatted categories text
        """
        categories = self.get_all_categories(session)
        
        if not categories:
            return "No categories available"
        
        categories_list = []
        for category in categories:
            category_info = f"ID: {category.id}, Name: {category.name}"
            if category.description:
                category_info += f", Description: {category.description}"
            categories_list.append(category_info)
        
        return "\n".join(categories_list)
    
    def get_by_name(self, session: Session, name: str) -> Optional[ActivityCategory]:
        """
        Get category by name.
        
        Args:
            session: Database session
            name: Category name
            
        Returns:
            ActivityCategory if found, None otherwise
        """
        return session.query(self.model_class).filter(self.model_class.name == name).first()