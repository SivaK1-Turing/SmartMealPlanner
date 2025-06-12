"""
Tests for the SQLAlchemy models.
"""

import json
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from mealplanner.models import (
    Base, Recipe, Ingredient, Plan, MealType, DietaryTag,
    create_recipe, create_ingredient, create_plan,
    recipe_ingredients
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestRecipeModel:
    """Test the Recipe model."""
    
    def test_recipe_creation(self, session):
        """Test creating a basic recipe."""
        recipe = Recipe(
            title="Test Recipe",
            description="A test recipe",
            prep_time=15,
            cook_time=30,
            servings=4,
            cuisine="Italian"
        )
        
        session.add(recipe)
        session.commit()
        
        assert recipe.id is not None
        assert recipe.title == "Test Recipe"
        assert recipe.total_time == 45
        assert recipe.created_at is not None
        assert recipe.updated_at is not None
    
    def test_recipe_dietary_tags(self, session):
        """Test dietary tags functionality."""
        recipe = Recipe(title="Vegan Recipe")
        
        # Test setting dietary tags
        tags = ["vegan", "gluten_free"]
        recipe.set_dietary_tags_list(tags)
        
        session.add(recipe)
        session.commit()
        
        # Test getting dietary tags
        retrieved_tags = recipe.get_dietary_tags_list()
        assert retrieved_tags == tags
        
        # Test empty tags
        recipe.set_dietary_tags_list([])
        assert recipe.dietary_tags is None
        assert recipe.get_dietary_tags_list() == []
    
    def test_recipe_total_time_calculation(self, session):
        """Test total time calculation with different scenarios."""
        # Both prep and cook time
        recipe1 = Recipe(title="Recipe 1", prep_time=10, cook_time=20)
        assert recipe1.total_time == 30
        
        # Only prep time
        recipe2 = Recipe(title="Recipe 2", prep_time=15)
        assert recipe2.total_time == 15
        
        # Only cook time
        recipe3 = Recipe(title="Recipe 3", cook_time=25)
        assert recipe3.total_time == 25
        
        # No times
        recipe4 = Recipe(title="Recipe 4")
        assert recipe4.total_time is None
    
    def test_recipe_repr(self, session):
        """Test recipe string representation."""
        recipe = Recipe(title="Test Recipe", cuisine="Italian")
        session.add(recipe)
        session.commit()
        
        repr_str = repr(recipe)
        assert "Test Recipe" in repr_str
        assert "Italian" in repr_str
        assert str(recipe.id) in repr_str


class TestIngredientModel:
    """Test the Ingredient model."""
    
    def test_ingredient_creation(self, session):
        """Test creating a basic ingredient."""
        ingredient = Ingredient(
            name="Tomato",
            category="Vegetables",
            calories_per_100g=18.0,
            protein_per_100g=0.9
        )
        
        session.add(ingredient)
        session.commit()
        
        assert ingredient.id is not None
        assert ingredient.name == "Tomato"
        assert ingredient.category == "Vegetables"
        assert ingredient.created_at is not None
    
    def test_ingredient_uniqueness(self, session):
        """Test that ingredient names are unique."""
        ingredient1 = Ingredient(name="Salt")
        ingredient2 = Ingredient(name="Salt")
        
        session.add(ingredient1)
        session.commit()
        
        session.add(ingredient2)
        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()
    
    def test_ingredient_repr(self, session):
        """Test ingredient string representation."""
        ingredient = Ingredient(name="Garlic", category="Herbs")
        session.add(ingredient)
        session.commit()
        
        repr_str = repr(ingredient)
        assert "Garlic" in repr_str
        assert "Herbs" in repr_str


class TestPlanModel:
    """Test the Plan model."""
    
    def test_plan_creation(self, session):
        """Test creating a meal plan."""
        # Create a recipe first
        recipe = Recipe(title="Breakfast Recipe")
        session.add(recipe)
        session.commit()
        
        # Create a plan
        plan = Plan(
            date=date(2024, 1, 15),
            meal_type=MealType.BREAKFAST,
            recipe_id=recipe.id,
            servings=2,
            notes="Special breakfast"
        )
        
        session.add(plan)
        session.commit()
        
        assert plan.id is not None
        assert plan.date == date(2024, 1, 15)
        assert plan.meal_type == MealType.BREAKFAST
        assert plan.servings == 2
        assert plan.completed is False
    
    def test_plan_recipe_relationship(self, session):
        """Test the relationship between Plan and Recipe."""
        recipe = Recipe(title="Lunch Recipe")
        session.add(recipe)
        session.commit()
        
        plan = Plan(
            date=date(2024, 1, 15),
            meal_type=MealType.LUNCH,
            recipe_id=recipe.id
        )
        session.add(plan)
        session.commit()
        
        # Test relationship
        assert plan.recipe.title == "Lunch Recipe"
        assert len(recipe.plans) == 1
        assert recipe.plans[0].meal_type == MealType.LUNCH
    
    def test_plan_date_queries(self, session):
        """Test date-based plan queries."""
        # Create recipes
        recipe1 = Recipe(title="Recipe 1")
        recipe2 = Recipe(title="Recipe 2")
        session.add_all([recipe1, recipe2])
        session.commit()
        
        # Create plans for different dates
        plan1 = Plan(date=date(2024, 1, 15), meal_type=MealType.BREAKFAST, recipe_id=recipe1.id)
        plan2 = Plan(date=date(2024, 1, 15), meal_type=MealType.LUNCH, recipe_id=recipe2.id)
        plan3 = Plan(date=date(2024, 1, 16), meal_type=MealType.DINNER, recipe_id=recipe1.id)
        
        session.add_all([plan1, plan2, plan3])
        session.commit()
        
        # Test get_plans_for_date
        plans_jan_15 = Plan.get_plans_for_date(session, date(2024, 1, 15))
        assert len(plans_jan_15) == 2
        assert plans_jan_15[0].meal_type == MealType.BREAKFAST  # Should be ordered
        
        # Test get_plans_for_date_range
        plans_range = Plan.get_plans_for_date_range(session, date(2024, 1, 15), date(2024, 1, 16))
        assert len(plans_range) == 3
    
    def test_plan_repr(self, session):
        """Test plan string representation."""
        recipe = Recipe(title="Test Recipe")
        session.add(recipe)
        session.commit()
        
        plan = Plan(
            date=date(2024, 1, 15),
            meal_type=MealType.DINNER,
            recipe_id=recipe.id
        )
        session.add(plan)
        session.commit()
        
        repr_str = repr(plan)
        assert "2024-01-15" in repr_str
        assert "dinner" in repr_str
        assert str(recipe.id) in repr_str


class TestRecipeIngredientRelationship:
    """Test the many-to-many relationship between recipes and ingredients."""
    
    def test_recipe_ingredient_association(self, session):
        """Test associating recipes with ingredients."""
        # Create recipe and ingredients
        recipe = Recipe(title="Pasta Recipe")
        ingredient1 = Ingredient(name="Pasta")
        ingredient2 = Ingredient(name="Tomato Sauce")
        
        session.add_all([recipe, ingredient1, ingredient2])
        session.commit()
        
        # Associate ingredients with recipe
        recipe.ingredients.append(ingredient1)
        recipe.ingredients.append(ingredient2)
        session.commit()
        
        # Test relationships
        assert len(recipe.ingredients) == 2
        assert ingredient1 in recipe.ingredients
        assert ingredient2 in recipe.ingredients
        
        # Test reverse relationship
        assert recipe in ingredient1.recipes
        assert recipe in ingredient2.recipes


class TestModelUtilityFunctions:
    """Test utility functions for model operations."""
    
    def test_create_recipe_function(self, session):
        """Test the create_recipe utility function."""
        recipe = create_recipe(
            session,
            title="Utility Recipe",
            description="Created with utility function",
            prep_time=10,
            servings=4,
            dietary_tags=["vegetarian", "quick"]
        )
        
        assert recipe.id is not None
        assert recipe.title == "Utility Recipe"
        assert recipe.get_dietary_tags_list() == ["vegetarian", "quick"]
    
    def test_create_ingredient_function(self, session):
        """Test the create_ingredient utility function."""
        ingredient = create_ingredient(
            session,
            name="Utility Ingredient",
            category="Test Category"
        )
        
        assert ingredient.id is not None
        assert ingredient.name == "Utility Ingredient"
        assert ingredient.category == "Test Category"
    
    def test_create_ingredient_duplicate(self, session):
        """Test creating duplicate ingredient returns existing one."""
        # Create first ingredient
        ingredient1 = create_ingredient(session, name="Duplicate Test")
        session.commit()
        
        # Try to create duplicate
        ingredient2 = create_ingredient(session, name="Duplicate Test")
        
        assert ingredient1.id == ingredient2.id
    
    def test_create_plan_function(self, session):
        """Test the create_plan utility function."""
        # Create recipe first
        recipe = Recipe(title="Plan Recipe")
        session.add(recipe)
        session.commit()
        
        plan = create_plan(
            session,
            date=date(2024, 1, 15),
            meal_type=MealType.DINNER,
            recipe_id=recipe.id,
            servings=3,
            notes="Test plan"
        )
        
        assert plan.id is not None
        assert plan.date == date(2024, 1, 15)
        assert plan.meal_type == MealType.DINNER
        assert plan.servings == 3
        assert plan.notes == "Test plan"


class TestEnums:
    """Test enum functionality."""
    
    def test_meal_type_enum(self):
        """Test MealType enum values."""
        assert MealType.BREAKFAST.value == "breakfast"
        assert MealType.LUNCH.value == "lunch"
        assert MealType.DINNER.value == "dinner"
        assert MealType.SNACK.value == "snack"
    
    def test_dietary_tag_enum(self):
        """Test DietaryTag enum values."""
        assert DietaryTag.VEGETARIAN.value == "vegetarian"
        assert DietaryTag.VEGAN.value == "vegan"
        assert DietaryTag.GLUTEN_FREE.value == "gluten_free"
