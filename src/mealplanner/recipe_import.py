"""
Recipe import functionality for the Smart Meal Planner application.

Handles importing recipes from JSON files, CSV files, and URLs with validation and deduplication.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from .database import get_db_session
from .models import Recipe, Ingredient, create_recipe, create_ingredient

logger = logging.getLogger(__name__)


class RecipeImportError(Exception):
    """Raised when recipe import fails."""
    pass


class RecipeValidator:
    """Validates recipe data before import."""
    
    REQUIRED_FIELDS = ['title']
    OPTIONAL_FIELDS = [
        'description', 'prep_time', 'cook_time', 'servings', 'cuisine',
        'dietary_tags', 'instructions', 'source_url', 'image_url',
        'calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium'
    ]
    
    @classmethod
    def validate_recipe(cls, recipe_data: Dict[str, Any], line_number: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        Validate recipe data.
        
        Args:
            recipe_data: Dictionary containing recipe data
            line_number: Optional line number for error reporting
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        line_prefix = f"Line {line_number}: " if line_number else ""
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in recipe_data or not recipe_data[field]:
                errors.append(f"{line_prefix}Missing required field: {field}")
        
        # Validate data types
        if 'title' in recipe_data and not isinstance(recipe_data['title'], str):
            errors.append(f"{line_prefix}Title must be a string")
        
        # Validate numeric fields
        numeric_fields = ['prep_time', 'cook_time', 'servings', 'calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium']
        for field in numeric_fields:
            if field in recipe_data and recipe_data[field] is not None:
                try:
                    float(recipe_data[field])
                except (ValueError, TypeError):
                    errors.append(f"{line_prefix}Field '{field}' must be a number")
        
        # Validate dietary tags
        if 'dietary_tags' in recipe_data and recipe_data['dietary_tags'] is not None:
            if isinstance(recipe_data['dietary_tags'], str):
                # Try to parse as JSON
                try:
                    json.loads(recipe_data['dietary_tags'])
                except json.JSONDecodeError:
                    # If not JSON, treat as comma-separated string
                    pass
            elif not isinstance(recipe_data['dietary_tags'], list):
                errors.append(f"{line_prefix}Dietary tags must be a list or comma-separated string")
        
        return len(errors) == 0, errors
    
    @classmethod
    def normalize_recipe_data(cls, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize recipe data for database insertion.
        
        Args:
            recipe_data: Raw recipe data
            
        Returns:
            Normalized recipe data
        """
        normalized = {}
        
        # Copy valid fields
        for field in cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS:
            if field in recipe_data and recipe_data[field] is not None:
                normalized[field] = recipe_data[field]
        
        # Convert numeric fields
        numeric_fields = ['prep_time', 'cook_time', 'servings']
        for field in numeric_fields:
            if field in normalized:
                try:
                    normalized[field] = int(float(normalized[field]))
                except (ValueError, TypeError):
                    normalized[field] = None
        
        # Convert float fields
        float_fields = ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium']
        for field in float_fields:
            if field in normalized:
                try:
                    normalized[field] = float(normalized[field])
                except (ValueError, TypeError):
                    normalized[field] = None
        
        # Handle dietary tags
        if 'dietary_tags' in normalized:
            if isinstance(normalized['dietary_tags'], str):
                # Try to parse as JSON first
                try:
                    tags = json.loads(normalized['dietary_tags'])
                    if isinstance(tags, list):
                        normalized['dietary_tags'] = tags
                    else:
                        # Treat as comma-separated string
                        normalized['dietary_tags'] = [tag.strip() for tag in normalized['dietary_tags'].split(',')]
                except json.JSONDecodeError:
                    # Treat as comma-separated string
                    normalized['dietary_tags'] = [tag.strip() for tag in normalized['dietary_tags'].split(',')]
        
        return normalized


class RecipeDeduplicator:
    """Handles recipe deduplication logic."""
    
    @staticmethod
    def find_duplicate_recipes(session: Session, recipe_data: Dict[str, Any]) -> List[Recipe]:
        """
        Find potential duplicate recipes based on title and ingredients.
        
        Args:
            session: Database session
            recipe_data: Recipe data to check
            
        Returns:
            List of potential duplicate recipes
        """
        title = recipe_data.get('title', '').strip().lower()
        
        # Find recipes with identical titles
        duplicates = session.query(Recipe).filter(
            Recipe.title.ilike(f"%{title}%")
        ).all()
        
        # TODO: In future, could also check ingredient similarity
        return duplicates
    
    @staticmethod
    def is_duplicate(session: Session, recipe_data: Dict[str, Any]) -> bool:
        """
        Check if a recipe is a duplicate.
        
        Args:
            session: Database session
            recipe_data: Recipe data to check
            
        Returns:
            True if recipe is likely a duplicate
        """
        duplicates = RecipeDeduplicator.find_duplicate_recipes(session, recipe_data)
        
        # For now, consider exact title matches as duplicates
        title = recipe_data.get('title', '').strip().lower()
        for recipe in duplicates:
            if recipe.title.strip().lower() == title:
                return True
        
        return False


class RecipeImporter:
    """Main recipe import functionality."""
    
    def __init__(self):
        self.validator = RecipeValidator()
        self.deduplicator = RecipeDeduplicator()
    
    def import_from_json(self, file_path: Union[str, Path], skip_duplicates: bool = True) -> Tuple[int, int, List[str]]:
        """
        Import recipes from a JSON file.
        
        Args:
            file_path: Path to JSON file
            skip_duplicates: Whether to skip duplicate recipes
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise RecipeImportError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RecipeImportError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise RecipeImportError(f"Error reading file: {e}")
        
        # Handle both single recipe and list of recipes
        if isinstance(data, dict):
            recipes_data = [data]
        elif isinstance(data, list):
            recipes_data = data
        else:
            raise RecipeImportError("JSON file must contain a recipe object or array of recipes")
        
        return self._import_recipes(recipes_data, skip_duplicates)
    
    def import_from_csv(self, file_path: Union[str, Path], skip_duplicates: bool = True) -> Tuple[int, int, List[str]]:
        """
        Import recipes from a CSV file.
        
        Args:
            file_path: Path to CSV file
            skip_duplicates: Whether to skip duplicate recipes
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise RecipeImportError(f"File not found: {file_path}")
        
        recipes_data = []
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for line_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                    # Remove empty values
                    recipe_data = {k: v for k, v in row.items() if v and v.strip()}
                    
                    if recipe_data:  # Skip empty rows
                        is_valid, validation_errors = self.validator.validate_recipe(recipe_data, line_num)
                        if is_valid:
                            recipes_data.append(self.validator.normalize_recipe_data(recipe_data))
                        else:
                            errors.extend(validation_errors)
                    
        except Exception as e:
            raise RecipeImportError(f"Error reading CSV file: {e}")
        
        imported, skipped, import_errors = self._import_recipes(recipes_data, skip_duplicates)
        errors.extend(import_errors)
        
        return imported, skipped, errors
    
    def import_from_url(self, url: str, skip_duplicates: bool = True, timeout: int = 30) -> Tuple[int, int, List[str]]:
        """
        Import recipes from a URL.
        
        Args:
            url: URL to fetch recipe data from
            skip_duplicates: Whether to skip duplicate recipes
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise RecipeImportError(f"Invalid URL: {url}")
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        except (requests.exceptions.RequestException, Exception) as e:
            raise RecipeImportError(f"Error fetching URL: {e}")
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise RecipeImportError(f"Invalid JSON response from URL: {e}")
        
        # Handle both single recipe and list of recipes
        if isinstance(data, dict):
            recipes_data = [data]
        elif isinstance(data, list):
            recipes_data = data
        else:
            raise RecipeImportError("URL must return a recipe object or array of recipes")
        
        return self._import_recipes(recipes_data, skip_duplicates)
    
    def _import_recipes(self, recipes_data: List[Dict[str, Any]], skip_duplicates: bool) -> Tuple[int, int, List[str]]:
        """
        Import a list of recipe data.
        
        Args:
            recipes_data: List of recipe dictionaries
            skip_duplicates: Whether to skip duplicate recipes
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        imported_count = 0
        skipped_count = 0
        errors = []
        
        with get_db_session() as session:
            for i, recipe_data in enumerate(recipes_data, start=1):
                try:
                    # Validate recipe data
                    is_valid, validation_errors = self.validator.validate_recipe(recipe_data, i)
                    if not is_valid:
                        errors.extend(validation_errors)
                        continue
                    
                    # Normalize data
                    normalized_data = self.validator.normalize_recipe_data(recipe_data)
                    
                    # Check for duplicates
                    if skip_duplicates and self.deduplicator.is_duplicate(session, normalized_data):
                        skipped_count += 1
                        logger.info(f"Skipped duplicate recipe: {normalized_data.get('title')}")
                        continue
                    
                    # Create recipe
                    recipe = create_recipe(session, **normalized_data)
                    imported_count += 1
                    logger.info(f"Imported recipe: {recipe.title}")
                    
                except Exception as e:
                    errors.append(f"Recipe {i}: Error importing recipe: {e}")
                    logger.error(f"Error importing recipe {i}: {e}")
        
        return imported_count, skipped_count, errors
