"""
Tests for the recipe management module.
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from mealplanner.models import Base, Recipe, Plan, MealType
from mealplanner.recipe_management import RecipeManager, RecipeFormatter


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


@pytest.fixture
def sample_recipes(session):
    """Create sample recipes for testing."""
    recipes = [
        Recipe(
            title="Italian Pasta",
            description="Delicious pasta dish",
            prep_time=15,
            cook_time=20,
            servings=4,
            cuisine="Italian",
            dietary_tags='["vegetarian"]',
            calories=450
        ),
        Recipe(
            title="Quick Salad",
            description="Fresh and healthy salad",
            prep_time=10,
            servings=2,
            cuisine="Mediterranean",
            dietary_tags='["vegan", "healthy"]',
            calories=200
        ),
        Recipe(
            title="Slow Cooked Stew",
            description="Hearty beef stew",
            prep_time=30,
            cook_time=120,
            servings=6,
            cuisine="American",
            calories=380
        )
    ]
    
    for recipe in recipes:
        session.add(recipe)
    session.commit()
    
    return recipes


class TestRecipeManager:
    """Test the RecipeManager class."""
    
    def test_get_recipe_by_id_exists(self, sample_recipes):
        """Test getting a recipe by ID when it exists."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = sample_recipes[0]
            
            recipe = RecipeManager.get_recipe_by_id(1)
            assert recipe is not None
            assert recipe.title == "Italian Pasta"
    
    def test_get_recipe_by_id_not_exists(self):
        """Test getting a recipe by ID when it doesn't exist."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            recipe = RecipeManager.get_recipe_by_id(999)
            assert recipe is None
    
    def test_list_recipes_basic(self, sample_recipes):
        """Test basic recipe listing."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 3
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_recipes
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj

            recipes, total_count, total_pages = RecipeManager.list_recipes(page=1, per_page=10)

            assert len(recipes) == 3
            assert total_count == 3
            assert total_pages == 1
    
    def test_list_recipes_with_cuisine_filter(self, sample_recipes):
        """Test recipe listing with cuisine filter."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_recipes[0]]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            recipes, total_count, total_pages = RecipeManager.list_recipes(cuisine="Italian")
            
            assert len(recipes) == 1
            assert recipes[0].title == "Italian Pasta"
    
    def test_list_recipes_with_max_time_filter(self, sample_recipes):
        """Test recipe listing with max time filter."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_recipes[:2]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            recipes, total_count, total_pages = RecipeManager.list_recipes(max_time=60)
            
            assert len(recipes) == 2
    
    def test_list_recipes_with_search(self, sample_recipes):
        """Test recipe listing with search term."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_recipes[1]]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            recipes, total_count, total_pages = RecipeManager.list_recipes(search="salad")
            
            assert len(recipes) == 1
            assert recipes[0].title == "Quick Salad"
    
    def test_list_recipes_pagination(self, sample_recipes):
        """Test recipe listing with pagination."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_query = MagicMock()
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 3
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_recipes[1:3]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            recipes, total_count, total_pages = RecipeManager.list_recipes(page=2, per_page=2)
            
            assert len(recipes) == 2
            assert total_count == 3
            assert total_pages == 2
    
    def test_search_recipes(self, sample_recipes):
        """Test recipe search functionality."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_recipes[0]]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            recipes, total_count, total_pages = RecipeManager.search_recipes("pasta")
            
            assert len(recipes) == 1
            assert recipes[0].title == "Italian Pasta"
    
    def test_update_recipe_success(self, sample_recipes):
        """Test successful recipe update."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = sample_recipes[0]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            updates = {"title": "Updated Pasta", "prep_time": 20}
            recipe = RecipeManager.update_recipe(1, updates)
            
            assert recipe is not None
            assert recipe.title == "Updated Pasta"
    
    def test_update_recipe_not_found(self):
        """Test updating non-existent recipe."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            recipe = RecipeManager.update_recipe(999, {"title": "New Title"})
            assert recipe is None
    
    def test_update_recipe_dietary_tags(self, sample_recipes):
        """Test updating recipe with dietary tags."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = sample_recipes[0]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            updates = {"dietary_tags": ["vegan", "healthy"]}
            recipe = RecipeManager.update_recipe(1, updates)
            
            assert recipe is not None
            # The set_dietary_tags_list method should be called
    
    def test_delete_recipe_success(self, sample_recipes):
        """Test successful recipe deletion."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = sample_recipes[0]
            mock_session_obj.query.return_value.filter.return_value.count.return_value = 0
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            success = RecipeManager.delete_recipe(1)
            assert success is True
    
    def test_delete_recipe_not_found(self):
        """Test deleting non-existent recipe."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            success = RecipeManager.delete_recipe(999)
            assert success is False
    
    def test_get_recipe_statistics(self, sample_recipes):
        """Test getting recipe statistics."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.count.return_value = 3
            mock_session_obj.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
                ("Italian", 1), ("Mediterranean", 1), ("American", 1)
            ]
            mock_session_obj.query.return_value.filter.return_value.scalar.return_value = 18.3
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            stats = RecipeManager.get_recipe_statistics()
            
            assert stats['total_recipes'] == 3
            assert 'cuisines' in stats
            assert stats['avg_prep_time'] == 18.3
    
    def test_get_recipes_by_cuisine(self, sample_recipes):
        """Test getting recipes by cuisine."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_recipes[0]]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            recipes = RecipeManager.get_recipes_by_cuisine("Italian")
            
            assert len(recipes) == 1
            assert recipes[0].title == "Italian Pasta"
    
    def test_get_recipes_by_dietary_tag(self, sample_recipes):
        """Test getting recipes by dietary tag."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_recipes[1]]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            recipes = RecipeManager.get_recipes_by_dietary_tag("vegan")
            
            assert len(recipes) == 1
            assert recipes[0].title == "Quick Salad"
    
    def test_get_quick_recipes(self, sample_recipes):
        """Test getting quick recipes."""
        with patch('mealplanner.recipe_management.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.order_by.return_value.all.return_value = sample_recipes[:2]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            recipes = RecipeManager.get_quick_recipes(max_time=60)
            
            assert len(recipes) == 2


class TestRecipeFormatter:
    """Test the RecipeFormatter class."""
    
    def test_format_recipe_summary(self, sample_recipes):
        """Test formatting recipe summary."""
        recipe = sample_recipes[0]
        summary = RecipeFormatter.format_recipe_summary(recipe)
        
        assert recipe.title in summary
        assert str(recipe.id) in summary
        assert "35 min" in summary  # total time
        assert recipe.cuisine in summary
    
    def test_format_recipe_summary_no_time(self, sample_recipes):
        """Test formatting recipe summary with no time info."""
        recipe = sample_recipes[1]  # Only has prep_time
        summary = RecipeFormatter.format_recipe_summary(recipe)

        assert recipe.title in summary
        assert "10 min" in summary  # Should show prep time
    
    def test_format_recipe_details(self, sample_recipes):
        """Test formatting detailed recipe information."""
        recipe = sample_recipes[0]
        details = RecipeFormatter.format_recipe_details(recipe)
        
        assert recipe.title in details
        assert recipe.description in details
        assert recipe.cuisine in details
        assert str(recipe.servings) in details
        assert "Prep: 15 min" in details
        assert "Cook: 20 min" in details
        assert "Total: 35 min" in details
        assert "Calories: 450" in details
    
    def test_format_recipe_details_minimal(self):
        """Test formatting recipe with minimal information."""
        recipe = Recipe(id=1, title="Minimal Recipe")
        details = RecipeFormatter.format_recipe_details(recipe)
        
        assert "Minimal Recipe" in details
        assert "ID: 1" in details
        # Should not contain optional fields that are None
