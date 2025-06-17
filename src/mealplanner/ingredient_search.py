"""
Ingredient search and filtering functionality for the Smart Meal Planner application.

Handles advanced ingredient search with nutritional filtering, category filtering,
and dietary restriction compatibility.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from .database import get_db_session
from .models import Ingredient, Recipe, recipe_ingredients

logger = logging.getLogger(__name__)


class IngredientSearchCriteria:
    """Encapsulates ingredient search criteria."""
    
    def __init__(
        self,
        search_term: Optional[str] = None,
        category: Optional[str] = None,
        min_calories: Optional[float] = None,
        max_calories: Optional[float] = None,
        min_protein: Optional[float] = None,
        max_protein: Optional[float] = None,
        min_carbs: Optional[float] = None,
        max_carbs: Optional[float] = None,
        min_fat: Optional[float] = None,
        max_fat: Optional[float] = None,
        min_fiber: Optional[float] = None,
        max_fiber: Optional[float] = None,
        dietary_restrictions: Optional[List[str]] = None,
        sort_by: str = 'name',
        sort_order: str = 'asc'
    ):
        """
        Initialize search criteria.
        
        Args:
            search_term: Text to search in ingredient names
            category: Filter by ingredient category
            min_calories: Minimum calories per 100g
            max_calories: Maximum calories per 100g
            min_protein: Minimum protein per 100g
            max_protein: Maximum protein per 100g
            min_carbs: Minimum carbs per 100g
            max_carbs: Maximum carbs per 100g
            min_fat: Minimum fat per 100g
            max_fat: Maximum fat per 100g
            min_fiber: Minimum fiber per 100g
            max_fiber: Maximum fiber per 100g
            dietary_restrictions: List of dietary restrictions to check compatibility
            sort_by: Field to sort by ('name', 'category', 'calories', 'protein')
            sort_order: Sort order ('asc' or 'desc')
        """
        self.search_term = search_term
        self.category = category
        self.min_calories = min_calories
        self.max_calories = max_calories
        self.min_protein = min_protein
        self.max_protein = max_protein
        self.min_carbs = min_carbs
        self.max_carbs = max_carbs
        self.min_fat = min_fat
        self.max_fat = max_fat
        self.min_fiber = min_fiber
        self.max_fiber = max_fiber
        self.dietary_restrictions = dietary_restrictions or []
        self.sort_by = sort_by
        self.sort_order = sort_order


class IngredientSearcher:
    """Handles ingredient search and filtering operations."""
    
    @staticmethod
    def search_ingredients(
        criteria: IngredientSearchCriteria,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Ingredient], int, int]:
        """
        Search ingredients based on criteria with pagination.
        
        Args:
            criteria: Search criteria object
            page: Page number (1-based)
            per_page: Number of ingredients per page
            
        Returns:
            Tuple of (ingredients, total_count, total_pages)
        """
        with get_db_session() as session:
            query = session.query(Ingredient)
            
            # Apply text search
            if criteria.search_term:
                search_term = f"%{criteria.search_term}%"
                query = query.filter(Ingredient.name.ilike(search_term))
            
            # Apply category filter
            if criteria.category:
                query = query.filter(Ingredient.category.ilike(f"%{criteria.category}%"))
            
            # Apply nutritional filters
            if criteria.min_calories is not None:
                query = query.filter(Ingredient.calories_per_100g >= criteria.min_calories)
            if criteria.max_calories is not None:
                query = query.filter(Ingredient.calories_per_100g <= criteria.max_calories)
            
            if criteria.min_protein is not None:
                query = query.filter(Ingredient.protein_per_100g >= criteria.min_protein)
            if criteria.max_protein is not None:
                query = query.filter(Ingredient.protein_per_100g <= criteria.max_protein)
            
            if criteria.min_carbs is not None:
                query = query.filter(Ingredient.carbs_per_100g >= criteria.min_carbs)
            if criteria.max_carbs is not None:
                query = query.filter(Ingredient.carbs_per_100g <= criteria.max_carbs)
            
            if criteria.min_fat is not None:
                query = query.filter(Ingredient.fat_per_100g >= criteria.min_fat)
            if criteria.max_fat is not None:
                query = query.filter(Ingredient.fat_per_100g <= criteria.max_fat)
            
            if criteria.min_fiber is not None:
                query = query.filter(Ingredient.fiber_per_100g >= criteria.min_fiber)
            if criteria.max_fiber is not None:
                query = query.filter(Ingredient.fiber_per_100g <= criteria.max_fiber)
            
            # Apply sorting
            sort_field = getattr(Ingredient, criteria.sort_by, Ingredient.name)
            if criteria.sort_order.lower() == 'desc':
                query = query.order_by(sort_field.desc().nulls_last())
            else:
                query = query.order_by(sort_field.asc().nulls_last())
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            ingredients = query.offset(offset).limit(per_page).all()
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page
            
            # Detach ingredients from session
            for ingredient in ingredients:
                session.expunge(ingredient)
            
            return ingredients, total_count, total_pages
    
    @staticmethod
    def find_ingredients_by_nutrition(
        min_protein: Optional[float] = None,
        max_calories: Optional[float] = None,
        min_fiber: Optional[float] = None
    ) -> List[Ingredient]:
        """
        Find ingredients that meet specific nutritional criteria.
        
        Args:
            min_protein: Minimum protein content per 100g
            max_calories: Maximum calories per 100g
            min_fiber: Minimum fiber content per 100g
            
        Returns:
            List of matching ingredients
        """
        criteria = IngredientSearchCriteria(
            min_protein=min_protein,
            max_calories=max_calories,
            min_fiber=min_fiber,
            sort_by='protein_per_100g',
            sort_order='desc'
        )
        
        ingredients, _, _ = IngredientSearcher.search_ingredients(criteria, per_page=1000)
        return ingredients
    
    @staticmethod
    def find_low_calorie_ingredients(max_calories: float = 50) -> List[Ingredient]:
        """
        Find low-calorie ingredients.
        
        Args:
            max_calories: Maximum calories per 100g
            
        Returns:
            List of low-calorie ingredients
        """
        return IngredientSearcher.find_ingredients_by_nutrition(max_calories=max_calories)
    
    @staticmethod
    def find_high_protein_ingredients(min_protein: float = 15) -> List[Ingredient]:
        """
        Find high-protein ingredients.
        
        Args:
            min_protein: Minimum protein content per 100g
            
        Returns:
            List of high-protein ingredients
        """
        return IngredientSearcher.find_ingredients_by_nutrition(min_protein=min_protein)
    
    @staticmethod
    def find_high_fiber_ingredients(min_fiber: float = 5) -> List[Ingredient]:
        """
        Find high-fiber ingredients.
        
        Args:
            min_fiber: Minimum fiber content per 100g
            
        Returns:
            List of high-fiber ingredients
        """
        return IngredientSearcher.find_ingredients_by_nutrition(min_fiber=min_fiber)
    
    @staticmethod
    def get_ingredients_by_category(category: str) -> List[Ingredient]:
        """
        Get all ingredients in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of ingredients in the category
        """
        with get_db_session() as session:
            ingredients = session.query(Ingredient).filter(
                Ingredient.category.ilike(f"%{category}%")
            ).order_by(Ingredient.name).all()
            
            # Detach from session
            for ingredient in ingredients:
                session.expunge(ingredient)
            
            return ingredients
    
    @staticmethod
    def get_ingredient_categories() -> List[str]:
        """
        Get all unique ingredient categories.
        
        Returns:
            List of category names
        """
        with get_db_session() as session:
            categories = session.query(Ingredient.category).filter(
                Ingredient.category.isnot(None)
            ).distinct().order_by(Ingredient.category).all()
            
            return [category[0] for category in categories if category[0]]
    
    @staticmethod
    def get_ingredients_used_in_recipes() -> List[Tuple[Ingredient, int]]:
        """
        Get ingredients and their usage count in recipes.
        
        Returns:
            List of tuples (ingredient, recipe_count)
        """
        with get_db_session() as session:
            results = session.query(
                Ingredient,
                func.count(recipe_ingredients.c.recipe_id).label('recipe_count')
            ).outerjoin(
                recipe_ingredients, Ingredient.id == recipe_ingredients.c.ingredient_id
            ).group_by(Ingredient.id).order_by(
                func.count(recipe_ingredients.c.recipe_id).desc()
            ).all()
            
            # Detach ingredients from session
            ingredient_usage = []
            for ingredient, count in results:
                session.expunge(ingredient)
                ingredient_usage.append((ingredient, count))
            
            return ingredient_usage
    
    @staticmethod
    def find_substitute_ingredients(
        ingredient_name: str,
        same_category: bool = True
    ) -> List[Ingredient]:
        """
        Find potential substitute ingredients.
        
        Args:
            ingredient_name: Name of the ingredient to find substitutes for
            same_category: Whether to limit to same category
            
        Returns:
            List of potential substitute ingredients
        """
        with get_db_session() as session:
            # Get the original ingredient
            original = session.query(Ingredient).filter(
                Ingredient.name.ilike(f"%{ingredient_name}%")
            ).first()
            
            if not original:
                return []
            
            query = session.query(Ingredient).filter(Ingredient.id != original.id)
            
            # Filter by category if requested
            if same_category and original.category:
                query = query.filter(Ingredient.category == original.category)
            
            # Find ingredients with similar nutritional profiles
            if original.calories_per_100g:
                calorie_range = original.calories_per_100g * 0.3  # 30% tolerance
                query = query.filter(
                    and_(
                        Ingredient.calories_per_100g >= original.calories_per_100g - calorie_range,
                        Ingredient.calories_per_100g <= original.calories_per_100g + calorie_range
                    )
                )
            
            substitutes = query.order_by(Ingredient.name).limit(10).all()
            
            # Detach from session
            for substitute in substitutes:
                session.expunge(substitute)
            
            return substitutes
