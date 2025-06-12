"""
SQLAlchemy ORM models for the Smart Meal Planner application.

Defines Recipe, Ingredient, and Plan models with appropriate relationships.
"""

import logging
from datetime import datetime, date
from typing import List, Optional
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Date, 
    ForeignKey, Table, Boolean, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

# Create the declarative base
Base = declarative_base()


class MealType(Enum):
    """Enumeration for meal types."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class DietaryTag(Enum):
    """Enumeration for dietary tags."""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    HIGH_PROTEIN = "high_protein"


# Association table for many-to-many relationship between recipes and ingredients
recipe_ingredients = Table(
    'recipe_ingredients',
    Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('ingredients.id'), primary_key=True),
    Column('quantity', Float, nullable=False, default=1.0),
    Column('unit', String(50), nullable=True),
    Column('notes', String(255), nullable=True)
)


class Recipe(Base):
    """Recipe model for storing recipe information."""
    
    __tablename__ = 'recipes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    prep_time = Column(Integer, nullable=True)  # in minutes
    cook_time = Column(Integer, nullable=True)  # in minutes
    servings = Column(Integer, nullable=True, default=1)
    cuisine = Column(String(100), nullable=True, index=True)
    dietary_tags = Column(String(255), nullable=True)  # JSON string of tags
    instructions = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Nutritional information (per serving)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)  # in grams
    carbs = Column(Float, nullable=True)    # in grams
    fat = Column(Float, nullable=True)      # in grams
    fiber = Column(Float, nullable=True)    # in grams
    sugar = Column(Float, nullable=True)    # in grams
    sodium = Column(Float, nullable=True)   # in mg
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    ingredients = relationship(
        "Ingredient",
        secondary=recipe_ingredients,
        back_populates="recipes",
        lazy="select"
    )
    plans = relationship("Plan", back_populates="recipe", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Recipe(id={self.id}, title='{self.title}', cuisine='{self.cuisine}')>"
    
    @property
    def total_time(self) -> Optional[int]:
        """Calculate total cooking time in minutes."""
        if self.prep_time and self.cook_time:
            return self.prep_time + self.cook_time
        elif self.prep_time:
            return self.prep_time
        elif self.cook_time:
            return self.cook_time
        return None
    
    def get_dietary_tags_list(self) -> List[str]:
        """Parse dietary tags from JSON string."""
        if not self.dietary_tags:
            return []
        try:
            import json
            return json.loads(self.dietary_tags)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_dietary_tags_list(self, tags: List[str]) -> None:
        """Set dietary tags as JSON string."""
        import json
        self.dietary_tags = json.dumps(tags) if tags else None


class Ingredient(Base):
    """Ingredient model for storing ingredient information."""
    
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Default nutritional information (per 100g)
    calories_per_100g = Column(Float, nullable=True)
    protein_per_100g = Column(Float, nullable=True)
    carbs_per_100g = Column(Float, nullable=True)
    fat_per_100g = Column(Float, nullable=True)
    fiber_per_100g = Column(Float, nullable=True)
    sugar_per_100g = Column(Float, nullable=True)
    sodium_per_100g = Column(Float, nullable=True)
    
    # Common units and conversions
    common_unit = Column(String(50), nullable=True)  # e.g., "cup", "tbsp", "piece"
    unit_weight_grams = Column(Float, nullable=True)  # weight of one common unit in grams
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    recipes = relationship(
        "Recipe",
        secondary=recipe_ingredients,
        back_populates="ingredients",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        return f"<Ingredient(id={self.id}, name='{self.name}', category='{self.category}')>"


class Plan(Base):
    """Plan model for meal scheduling."""
    
    __tablename__ = 'plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(SQLEnum(MealType), nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    servings = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="plans")
    
    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, date={self.date}, meal_type={self.meal_type.value}, recipe_id={self.recipe_id})>"
    
    @classmethod
    def get_plans_for_date_range(cls, session: Session, start_date: date, end_date: date) -> List['Plan']:
        """Get all plans within a date range."""
        return session.query(cls).filter(
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date, cls.meal_type).all()
    
    @classmethod
    def get_plans_for_date(cls, session: Session, target_date: date) -> List['Plan']:
        """Get all plans for a specific date."""
        return session.query(cls).filter(cls.date == target_date).order_by(cls.meal_type).all()


# Utility functions for model operations
def create_recipe(
    session: Session,
    title: str,
    description: Optional[str] = None,
    prep_time: Optional[int] = None,
    cook_time: Optional[int] = None,
    servings: Optional[int] = None,
    cuisine: Optional[str] = None,
    dietary_tags: Optional[List[str]] = None,
    **kwargs
) -> Recipe:
    """Create a new recipe with the given parameters."""
    recipe = Recipe(
        title=title,
        description=description,
        prep_time=prep_time,
        cook_time=cook_time,
        servings=servings,
        cuisine=cuisine,
        **kwargs
    )
    
    if dietary_tags:
        recipe.set_dietary_tags_list(dietary_tags)
    
    session.add(recipe)
    session.flush()  # Get the ID without committing
    logger.info(f"Created recipe: {recipe}")
    return recipe


def create_ingredient(
    session: Session,
    name: str,
    category: Optional[str] = None,
    **kwargs
) -> Ingredient:
    """Create a new ingredient with the given parameters."""
    # Check if ingredient already exists
    existing = session.query(Ingredient).filter(Ingredient.name == name).first()
    if existing:
        logger.warning(f"Ingredient '{name}' already exists with ID {existing.id}")
        return existing
    
    ingredient = Ingredient(name=name, category=category, **kwargs)
    session.add(ingredient)
    session.flush()  # Get the ID without committing
    logger.info(f"Created ingredient: {ingredient}")
    return ingredient


def create_plan(
    session: Session,
    date: date,
    meal_type: MealType,
    recipe_id: int,
    servings: int = 1,
    notes: Optional[str] = None
) -> Plan:
    """Create a new meal plan with the given parameters."""
    plan = Plan(
        date=date,
        meal_type=meal_type,
        recipe_id=recipe_id,
        servings=servings,
        notes=notes
    )
    
    session.add(plan)
    session.flush()  # Get the ID without committing
    logger.info(f"Created plan: {plan}")
    return plan
