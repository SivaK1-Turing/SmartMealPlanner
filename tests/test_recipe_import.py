"""
Tests for the recipe import module.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from mealplanner.models import Base, Recipe
from mealplanner.recipe_import import (
    RecipeValidator, RecipeDeduplicator, RecipeImporter, RecipeImportError
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
def sample_recipe_data():
    """Sample recipe data for testing."""
    return {
        "title": "Test Recipe",
        "description": "A test recipe",
        "prep_time": 15,
        "cook_time": 30,
        "servings": 4,
        "cuisine": "Italian",
        "dietary_tags": ["vegetarian", "quick"],
        "calories": 350.5,
        "protein": 12.0
    }


@pytest.fixture
def sample_json_file(tmp_path, sample_recipe_data):
    """Create a sample JSON file for testing."""
    json_file = tmp_path / "test_recipes.json"
    json_file.write_text(json.dumps([sample_recipe_data]))
    return json_file


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    csv_file = tmp_path / "test_recipes.csv"
    csv_content = """title,description,prep_time,cook_time,servings,cuisine,dietary_tags,calories
Test Recipe,A test recipe,15,30,4,Italian,"vegetarian,quick",350.5
Another Recipe,Another test recipe,10,20,2,Mexican,spicy,280"""
    csv_file.write_text(csv_content)
    return csv_file


class TestRecipeValidator:
    """Test the RecipeValidator class."""
    
    def test_validate_recipe_valid(self, sample_recipe_data):
        """Test validation of valid recipe data."""
        is_valid, errors = RecipeValidator.validate_recipe(sample_recipe_data)
        assert is_valid
        assert errors == []
    
    def test_validate_recipe_missing_title(self):
        """Test validation with missing title."""
        recipe_data = {"description": "No title"}
        is_valid, errors = RecipeValidator.validate_recipe(recipe_data, line_number=1)
        assert not is_valid
        assert "Line 1: Missing required field: title" in errors
    
    def test_validate_recipe_invalid_types(self):
        """Test validation with invalid data types."""
        recipe_data = {
            "title": 123,  # Should be string
            "prep_time": "not_a_number"  # Should be number
        }
        is_valid, errors = RecipeValidator.validate_recipe(recipe_data)
        assert not is_valid
        assert any("Title must be a string" in error for error in errors)
        assert any("prep_time" in error and "number" in error for error in errors)
    
    def test_validate_recipe_invalid_dietary_tags(self):
        """Test validation with invalid dietary tags."""
        recipe_data = {
            "title": "Test Recipe",
            "dietary_tags": 123  # Should be list or string
        }
        is_valid, errors = RecipeValidator.validate_recipe(recipe_data)
        assert not is_valid
        assert any("Dietary tags must be a list" in error for error in errors)
    
    def test_normalize_recipe_data(self, sample_recipe_data):
        """Test recipe data normalization."""
        normalized = RecipeValidator.normalize_recipe_data(sample_recipe_data)
        
        assert normalized["title"] == "Test Recipe"
        assert normalized["prep_time"] == 15
        assert normalized["calories"] == 350.5
        assert normalized["dietary_tags"] == ["vegetarian", "quick"]
    
    def test_normalize_dietary_tags_string(self):
        """Test normalization of dietary tags from string."""
        recipe_data = {
            "title": "Test Recipe",
            "dietary_tags": "vegetarian,quick,healthy"
        }
        normalized = RecipeValidator.normalize_recipe_data(recipe_data)
        assert normalized["dietary_tags"] == ["vegetarian", "quick", "healthy"]
    
    def test_normalize_dietary_tags_json_string(self):
        """Test normalization of dietary tags from JSON string."""
        recipe_data = {
            "title": "Test Recipe",
            "dietary_tags": '["vegetarian", "quick"]'
        }
        normalized = RecipeValidator.normalize_recipe_data(recipe_data)
        assert normalized["dietary_tags"] == ["vegetarian", "quick"]


class TestRecipeDeduplicator:
    """Test the RecipeDeduplicator class."""
    
    def test_find_duplicate_recipes_no_duplicates(self, session):
        """Test finding duplicates when none exist."""
        recipe_data = {"title": "Unique Recipe"}
        duplicates = RecipeDeduplicator.find_duplicate_recipes(session, recipe_data)
        assert duplicates == []
    
    def test_find_duplicate_recipes_with_duplicates(self, session):
        """Test finding duplicates when they exist."""
        # Create a recipe in the database
        existing_recipe = Recipe(title="Test Recipe")
        session.add(existing_recipe)
        session.commit()
        
        recipe_data = {"title": "Test Recipe"}
        duplicates = RecipeDeduplicator.find_duplicate_recipes(session, recipe_data)
        assert len(duplicates) == 1
        assert duplicates[0].title == "Test Recipe"
    
    def test_is_duplicate_exact_match(self, session):
        """Test duplicate detection with exact title match."""
        # Create a recipe in the database
        existing_recipe = Recipe(title="Test Recipe")
        session.add(existing_recipe)
        session.commit()
        
        recipe_data = {"title": "Test Recipe"}
        is_dup = RecipeDeduplicator.is_duplicate(session, recipe_data)
        assert is_dup
    
    def test_is_duplicate_no_match(self, session):
        """Test duplicate detection with no match."""
        recipe_data = {"title": "Unique Recipe"}
        is_dup = RecipeDeduplicator.is_duplicate(session, recipe_data)
        assert not is_dup


class TestRecipeImporter:
    """Test the RecipeImporter class."""
    
    def test_import_from_json_single_recipe(self, sample_json_file):
        """Test importing from JSON file with single recipe."""
        with patch('mealplanner.recipe_import.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            
            importer = RecipeImporter()
            imported, skipped, errors = importer.import_from_json(sample_json_file)
            
            assert imported == 1
            assert skipped == 0
            assert errors == []
    
    def test_import_from_json_file_not_found(self):
        """Test importing from non-existent JSON file."""
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="File not found"):
            importer.import_from_json("nonexistent.json")
    
    def test_import_from_json_invalid_json(self, tmp_path):
        """Test importing from invalid JSON file."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json")
        
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="Invalid JSON file"):
            importer.import_from_json(invalid_json)
    
    def test_import_from_csv(self, sample_csv_file):
        """Test importing from CSV file."""
        with patch('mealplanner.recipe_import.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            
            importer = RecipeImporter()
            imported, skipped, errors = importer.import_from_csv(sample_csv_file)
            
            assert imported == 2
            assert skipped == 0
            assert errors == []
    
    def test_import_from_csv_file_not_found(self):
        """Test importing from non-existent CSV file."""
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="File not found"):
            importer.import_from_csv("nonexistent.csv")
    
    @patch('mealplanner.recipe_import.requests.get')
    def test_import_from_url_success(self, mock_get):
        """Test importing from URL successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"title": "URL Recipe"}]
        mock_get.return_value = mock_response
        
        with patch('mealplanner.recipe_import.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            
            importer = RecipeImporter()
            imported, skipped, errors = importer.import_from_url("https://example.com/recipes.json")
            
            assert imported == 1
            assert skipped == 0
            assert errors == []
    
    @patch('mealplanner.recipe_import.requests.get')
    def test_import_from_url_invalid_url(self, mock_get):
        """Test importing from invalid URL."""
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="Invalid URL"):
            importer.import_from_url("not-a-url")
    
    @patch('mealplanner.recipe_import.requests.get')
    def test_import_from_url_request_error(self, mock_get):
        """Test importing from URL with request error."""
        mock_get.side_effect = Exception("Network error")
        
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="Error fetching URL"):
            importer.import_from_url("https://example.com/recipes.json")
    
    @patch('mealplanner.recipe_import.requests.get')
    def test_import_from_url_invalid_json(self, mock_get):
        """Test importing from URL with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        importer = RecipeImporter()
        
        with pytest.raises(RecipeImportError, match="Invalid JSON response"):
            importer.import_from_url("https://example.com/recipes.json")
    
    def test_import_recipes_with_duplicates(self, session):
        """Test importing recipes with duplicate detection."""
        # Create existing recipe
        existing_recipe = Recipe(title="Duplicate Recipe")
        session.add(existing_recipe)
        session.commit()
        
        recipes_data = [
            {"title": "New Recipe"},
            {"title": "Duplicate Recipe"},  # This should be skipped
            {"title": "Another New Recipe"}
        ]
        
        with patch('mealplanner.recipe_import.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = session
            
            importer = RecipeImporter()
            imported, skipped, errors = importer._import_recipes(recipes_data, skip_duplicates=True)
            
            assert imported == 2
            assert skipped == 1
            assert errors == []
    
    def test_import_recipes_validation_errors(self):
        """Test importing recipes with validation errors."""
        recipes_data = [
            {"title": "Valid Recipe"},
            {"description": "No title"},  # Invalid - missing title
            {"title": "Another Valid Recipe"}
        ]
        
        with patch('mealplanner.recipe_import.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            
            importer = RecipeImporter()
            imported, skipped, errors = importer._import_recipes(recipes_data, skip_duplicates=True)
            
            assert imported == 2
            assert skipped == 0
            assert len(errors) == 1
            assert "Missing required field: title" in errors[0]
