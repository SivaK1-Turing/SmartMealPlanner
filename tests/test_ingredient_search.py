"""
Tests for the ingredient search module.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from mealplanner.models import Base, Ingredient
from mealplanner.ingredient_search import (
    IngredientSearchCriteria, IngredientSearcher
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


@pytest.fixture
def sample_ingredients(session):
    """Create sample ingredients for testing."""
    ingredients = [
        Ingredient(
            name="Chicken Breast",
            category="Meat",
            calories_per_100g=165,
            protein_per_100g=31.0,
            carbs_per_100g=0.0,
            fat_per_100g=3.6,
            fiber_per_100g=0.0
        ),
        Ingredient(
            name="Broccoli",
            category="Vegetables",
            calories_per_100g=34,
            protein_per_100g=2.8,
            carbs_per_100g=7.0,
            fat_per_100g=0.4,
            fiber_per_100g=2.6
        ),
        Ingredient(
            name="Brown Rice",
            category="Grains",
            calories_per_100g=111,
            protein_per_100g=2.6,
            carbs_per_100g=23.0,
            fat_per_100g=0.9,
            fiber_per_100g=1.8
        ),
        Ingredient(
            name="Salmon",
            category="Fish",
            calories_per_100g=208,
            protein_per_100g=25.4,
            carbs_per_100g=0.0,
            fat_per_100g=12.4,
            fiber_per_100g=0.0
        ),
        Ingredient(
            name="Spinach",
            category="Vegetables",
            calories_per_100g=23,
            protein_per_100g=2.9,
            carbs_per_100g=3.6,
            fat_per_100g=0.4,
            fiber_per_100g=2.2
        )
    ]
    
    for ingredient in ingredients:
        session.add(ingredient)
    session.commit()
    
    return ingredients


class TestIngredientSearchCriteria:
    """Test the IngredientSearchCriteria class."""
    
    def test_criteria_initialization_defaults(self):
        """Test default initialization of search criteria."""
        criteria = IngredientSearchCriteria()
        
        assert criteria.search_term is None
        assert criteria.category is None
        assert criteria.min_calories is None
        assert criteria.max_calories is None
        assert criteria.dietary_restrictions == []
        assert criteria.sort_by == 'name'
        assert criteria.sort_order == 'asc'
    
    def test_criteria_initialization_with_values(self):
        """Test initialization with specific values."""
        criteria = IngredientSearchCriteria(
            search_term="chicken",
            category="Meat",
            min_calories=100,
            max_calories=200,
            min_protein=20,
            dietary_restrictions=["high_protein"],
            sort_by="protein_per_100g",
            sort_order="desc"
        )
        
        assert criteria.search_term == "chicken"
        assert criteria.category == "Meat"
        assert criteria.min_calories == 100
        assert criteria.max_calories == 200
        assert criteria.min_protein == 20
        assert criteria.dietary_restrictions == ["high_protein"]
        assert criteria.sort_by == "protein_per_100g"
        assert criteria.sort_order == "desc"


class TestIngredientSearcher:
    """Test the IngredientSearcher class."""
    
    def test_search_ingredients_no_criteria(self, sample_ingredients):
        """Test searching ingredients with no criteria."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 5
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_ingredients
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            criteria = IngredientSearchCriteria()
            ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(criteria)
            
            assert len(ingredients) == 5
            assert total_count == 5
            assert total_pages == 1
    
    def test_search_ingredients_with_search_term(self, sample_ingredients):
        """Test searching ingredients with search term."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[0]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            criteria = IngredientSearchCriteria(search_term="chicken")
            ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(criteria)
            
            assert len(ingredients) == 1
            assert ingredients[0].name == "Chicken Breast"
    
    def test_search_ingredients_with_category_filter(self, sample_ingredients):
        """Test searching ingredients with category filter."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[1], sample_ingredients[4]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            criteria = IngredientSearchCriteria(category="Vegetables")
            ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(criteria)
            
            assert len(ingredients) == 2
            assert all(ing.category == "Vegetables" for ing in ingredients)
    
    def test_search_ingredients_with_nutritional_filters(self, sample_ingredients):
        """Test searching ingredients with nutritional filters."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[0], sample_ingredients[3]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            criteria = IngredientSearchCriteria(min_protein=20, max_calories=250)
            ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(criteria)
            
            assert len(ingredients) == 2
    
    def test_search_ingredients_pagination(self, sample_ingredients):
        """Test ingredient search with pagination."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 5
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_ingredients[2:4]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            criteria = IngredientSearchCriteria()
            ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(
                criteria, page=2, per_page=2
            )
            
            assert len(ingredients) == 2
            assert total_count == 5
            assert total_pages == 3
    
    def test_find_ingredients_by_nutrition(self, sample_ingredients):
        """Test finding ingredients by nutritional criteria."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[0]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            ingredients = IngredientSearcher.find_ingredients_by_nutrition(
                min_protein=25, max_calories=200
            )
            
            assert len(ingredients) == 1
            assert ingredients[0].name == "Chicken Breast"
    
    def test_find_low_calorie_ingredients(self, sample_ingredients):
        """Test finding low-calorie ingredients."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[1], sample_ingredients[4]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            ingredients = IngredientSearcher.find_low_calorie_ingredients(max_calories=50)
            
            assert len(ingredients) == 2
    
    def test_find_high_protein_ingredients(self, sample_ingredients):
        """Test finding high-protein ingredients."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.offset.return_value.limit.return_value.all.return_value = [sample_ingredients[0], sample_ingredients[3]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            ingredients = IngredientSearcher.find_high_protein_ingredients(min_protein=15)
            
            assert len(ingredients) == 2
    
    def test_find_high_fiber_ingredients(self, sample_ingredients):
        """Test finding high-fiber ingredients."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.offset.return_value.limit.return_value.all.return_value = []
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            ingredients = IngredientSearcher.find_high_fiber_ingredients(min_fiber=5)
            
            assert len(ingredients) == 0
    
    def test_get_ingredients_by_category(self, sample_ingredients):
        """Test getting ingredients by category."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value.all.return_value = [sample_ingredients[1], sample_ingredients[4]]
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            ingredients = IngredientSearcher.get_ingredients_by_category("Vegetables")
            
            assert len(ingredients) == 2
            assert all(ing.category == "Vegetables" for ing in ingredients)
    
    def test_get_ingredient_categories(self, sample_ingredients):
        """Test getting all ingredient categories."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.distinct.return_value = mock_query
            mock_query.order_by.return_value.all.return_value = [
                ("Meat",), ("Vegetables",), ("Grains",), ("Fish",)
            ]
            mock_session_obj.query.return_value = mock_query
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            categories = IngredientSearcher.get_ingredient_categories()
            
            assert len(categories) == 4
            assert "Meat" in categories
            assert "Vegetables" in categories
    
    def test_find_substitute_ingredients(self, sample_ingredients):
        """Test finding substitute ingredients."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            
            # Mock finding the original ingredient
            mock_query.filter.return_value.first.return_value = sample_ingredients[0]  # Chicken Breast
            
            # Mock finding substitutes
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value.limit.return_value.all.return_value = [sample_ingredients[3]]  # Salmon
            
            mock_session_obj.query.return_value = mock_query
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            substitutes = IngredientSearcher.find_substitute_ingredients("Chicken Breast")
            
            assert len(substitutes) == 1
            assert substitutes[0].name == "Salmon"
    
    def test_find_substitute_ingredients_not_found(self):
        """Test finding substitutes for non-existent ingredient."""
        with patch('mealplanner.ingredient_search.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_obj.query.return_value = mock_query
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            substitutes = IngredientSearcher.find_substitute_ingredients("Nonexistent")
            
            assert len(substitutes) == 0
