"""
Base repository class providing common database operations.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from database import Base

# Generic type for model classes
ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """Abstract base class for repository pattern implementation."""
    
    def __init__(self, model_class: Type[ModelType]):
        """
        Initialize repository with model class.
        
        Args:
            model_class: SQLAlchemy model class
        """
        self.model_class = model_class
    
    def get_by_id(self, session: Session, id: int) -> Optional[ModelType]:
        """
        Get entity by ID.
        
        Args:
            session: Database session
            id: Entity ID
            
        Returns:
            Entity instance or None if not found
        """
        return session.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
    
    def get_all(
        self, 
        session: Session, 
        offset: int = 0, 
        limit: int = 100,
        order_by: str = 'id',
        order_direction: str = 'asc'
    ) -> List[ModelType]:
        """
        Get all entities with pagination and ordering.
        
        Args:
            session: Database session
            offset: Number of records to skip
            limit: Maximum number of records to return
            order_by: Column name to order by
            order_direction: 'asc' or 'desc'
            
        Returns:
            List of entity instances
        """
        query = session.query(self.model_class)
        
        # Apply ordering
        order_column = getattr(self.model_class, order_by, None)
        if order_column is not None:
            if order_direction.lower() == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        
        return query.offset(offset).limit(limit).all()
    
    def create(self, session: Session, **kwargs) -> ModelType:
        """
        Create new entity.
        
        Args:
            session: Database session
            **kwargs: Entity attributes
            
        Returns:
            Created entity instance
        """
        entity = self.model_class(**kwargs)
        session.add(entity)
        session.flush()  # Get the ID without committing
        return entity
    
    def update(
        self, 
        session: Session, 
        entity: ModelType, 
        **kwargs
    ) -> ModelType:
        """
        Update existing entity.
        
        Args:
            session: Database session
            entity: Entity instance to update
            **kwargs: Attributes to update
            
        Returns:
            Updated entity instance
        """
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        session.flush()
        return entity
    
    def delete(self, session: Session, entity: ModelType) -> None:
        """
        Delete entity.
        
        Args:
            session: Database session
            entity: Entity instance to delete
        """
        session.delete(entity)
        session.flush()
    
    def count(self, session: Session, **filters) -> int:
        """
        Count entities with optional filters.
        
        Args:
            session: Database session
            **filters: Filter conditions
            
        Returns:
            Count of matching entities
        """
        query = session.query(self.model_class)
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        
        return query.count()
    
    def exists(self, session: Session, **filters) -> bool:
        """
        Check if entity exists with given filters.
        
        Args:
            session: Database session
            **filters: Filter conditions
            
        Returns:
            True if entity exists, False otherwise
        """
        query = session.query(self.model_class)
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        
        return query.first() is not None
    
    def find_by(self, session: Session, **filters) -> List[ModelType]:
        """
        Find entities by filters.
        
        Args:
            session: Database session
            **filters: Filter conditions
            
        Returns:
            List of matching entities
        """
        query = session.query(self.model_class)
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        
        return query.all()
    
    def find_one_by(self, session: Session, **filters) -> Optional[ModelType]:
        """
        Find single entity by filters.
        
        Args:
            session: Database session
            **filters: Filter conditions
            
        Returns:
            Entity instance or None if not found
        """
        query = session.query(self.model_class)
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        
        return query.first()