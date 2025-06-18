"""
Ingredient management functionality for the Smart Meal Planner application.

Handles CRUD operations, bulk management, and nutritional data management for ingredients.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .database import get_db_session
from .models import Ingredient, Recipe, recipe_ingredients, create_ingredient

logger = logging.getLogger(__name__)


class IngredientManager:
    """Manages ingredient CRUD operations and queries."""
    
    @staticmethod
    def get_ingredient_by_id(ingredient_id: int) -> Optional[Ingredient]:
        """
        Get an ingredient by its ID.
        
        Args:
            ingredient_id: Ingredient ID
            
        Returns:
            Ingredient object or None if not found
        """
        with get_db_session() as session:
            ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
            if ingredient:
                session.expunge(ingredient)
            return ingredient
    
    @staticmethod
    def get_ingredient_by_name(name: str) -> Optional[Ingredient]:
        """
        Get an ingredient by its name.
        
        Args:
            name: Ingredient name
            
        Returns:
            Ingredient object or None if not found
        """
        with get_db_session() as session:
            ingredient = session.query(Ingredient).filter(
                Ingredient.name.ilike(f"%{name}%")
            ).first()
            if ingredient:
                session.expunge(ingredient)
            return ingredient
    
    @staticmethod
    def list_ingredients(
        page: int = 1,
        per_page: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = 'name',
        sort_order: str = 'asc'
    ) -> Tuple[List[Ingredient], int, int]:
        """
        List ingredients with filtering, pagination, and sorting.
        
        Args:
            page: Page number (1-based)
            per_page: Number of ingredients per page
            category: Filter by category
            search: Search term for ingredient names
            sort_by: Sort field ('name', 'category', 'calories_per_100g', 'protein_per_100g')
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Tuple of (ingredients, total_count, total_pages)
        """
        with get_db_session() as session:
            query = session.query(Ingredient)
            
            # Apply filters
            if category:
                query = query.filter(Ingredient.category.ilike(f"%{category}%"))
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(Ingredient.name.ilike(search_term))
            
            # Apply sorting
            sort_field = getattr(Ingredient, sort_by, Ingredient.name)
            if sort_order.lower() == 'desc':
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
    def create_ingredient(
        name: str,
        category: Optional[str] = None,
        calories_per_100g: Optional[float] = None,
        protein_per_100g: Optional[float] = None,
        carbs_per_100g: Optional[float] = None,
        fat_per_100g: Optional[float] = None,
        fiber_per_100g: Optional[float] = None,
        sugar_per_100g: Optional[float] = None,
        sodium_per_100g: Optional[float] = None,
        common_unit: Optional[str] = None,
        unit_weight_grams: Optional[float] = None
    ) -> Ingredient:
        """
        Create a new ingredient.

        Args:
            name: Ingredient name
            category: Ingredient category
            calories_per_100g: Calories per 100g
            protein_per_100g: Protein per 100g
            carbs_per_100g: Carbohydrates per 100g
            fat_per_100g: Fat per 100g
            fiber_per_100g: Fiber per 100g
            sugar_per_100g: Sugar per 100g
            sodium_per_100g: Sodium per 100g
            common_unit: Common unit (e.g., "cup", "tbsp")
            unit_weight_grams: Weight of one common unit in grams

        Returns:
            Created ingredient
        """
        with get_db_session() as session:
            ingredient = create_ingredient(
                session=session,
                name=name,
                category=category,
                calories_per_100g=calories_per_100g,
                protein_per_100g=protein_per_100g,
                carbs_per_100g=carbs_per_100g,
                fat_per_100g=fat_per_100g,
                fiber_per_100g=fiber_per_100g,
                sugar_per_100g=sugar_per_100g,
                sodium_per_100g=sodium_per_100g,
                common_unit=common_unit,
                unit_weight_grams=unit_weight_grams
            )
            session.commit()
            # Refresh to get the ID and then expunge
            session.refresh(ingredient)
            session.expunge(ingredient)
            return ingredient
    
    @staticmethod
    def update_ingredient(ingredient_id: int, updates: Dict[str, Any]) -> Optional[Ingredient]:
        """
        Update an ingredient with new data.
        
        Args:
            ingredient_id: Ingredient ID to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated ingredient or None if not found
        """
        with get_db_session() as session:
            ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
            
            if not ingredient:
                return None
            
            # Update fields
            for field, value in updates.items():
                if hasattr(ingredient, field):
                    setattr(ingredient, field, value)
            
            session.commit()
            session.refresh(ingredient)
            session.expunge(ingredient)
            logger.info(f"Updated ingredient: {ingredient.name}")
            return ingredient
    
    @staticmethod
    def delete_ingredient(ingredient_id: int) -> bool:
        """
        Delete an ingredient and its recipe associations.
        
        Args:
            ingredient_id: Ingredient ID to delete
            
        Returns:
            True if ingredient was deleted, False if not found
        """
        with get_db_session() as session:
            ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
            
            if not ingredient:
                return False
            
            # Check for recipe associations
            recipe_count = session.query(recipe_ingredients).filter(
                recipe_ingredients.c.ingredient_id == ingredient_id
            ).count()
            
            ingredient_name = ingredient.name
            session.delete(ingredient)
            session.commit()
            
            logger.info(f"Deleted ingredient: {ingredient_name} (was used in {recipe_count} recipes)")
            return True
    
    @staticmethod
    def get_ingredient_statistics() -> Dict[str, Any]:
        """
        Get statistics about ingredients in the database.
        
        Returns:
            Dictionary with ingredient statistics
        """
        with get_db_session() as session:
            total_ingredients = session.query(Ingredient).count()
            
            # Count by category
            category_counts = session.query(
                Ingredient.category,
                func.count(Ingredient.id).label('count')
            ).filter(Ingredient.category.isnot(None)).group_by(Ingredient.category).all()
            
            # Average nutritional values
            avg_calories = session.query(func.avg(Ingredient.calories_per_100g)).filter(
                Ingredient.calories_per_100g.isnot(None)
            ).scalar()
            
            avg_protein = session.query(func.avg(Ingredient.protein_per_100g)).filter(
                Ingredient.protein_per_100g.isnot(None)
            ).scalar()
            
            # Most used ingredients
            most_used = session.query(
                Ingredient.name,
                func.count(recipe_ingredients.c.recipe_id).label('usage_count')
            ).join(
                recipe_ingredients, Ingredient.id == recipe_ingredients.c.ingredient_id
            ).group_by(Ingredient.id, Ingredient.name).order_by(
                desc('usage_count')
            ).limit(5).all()
            
            return {
                'total_ingredients': total_ingredients,
                'categories': dict(category_counts),
                'avg_calories_per_100g': round(avg_calories, 1) if avg_calories else None,
                'avg_protein_per_100g': round(avg_protein, 1) if avg_protein else None,
                'most_used': [(name, count) for name, count in most_used]
            }
    
    @staticmethod
    def bulk_import_ingredients(ingredients_data: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Bulk import ingredients from a list of dictionaries.
        
        Args:
            ingredients_data: List of ingredient data dictionaries
            
        Returns:
            Tuple of (imported_count, errors)
        """
        imported_count = 0
        errors = []
        
        with get_db_session() as session:
            for i, ingredient_data in enumerate(ingredients_data, start=1):
                try:
                    # Validate required fields
                    if 'name' not in ingredient_data or not ingredient_data['name']:
                        errors.append(f"Ingredient {i}: Missing required field 'name'")
                        continue
                    
                    # Check if ingredient already exists
                    existing = session.query(Ingredient).filter(
                        Ingredient.name == ingredient_data['name']
                    ).first()
                    
                    if existing:
                        errors.append(f"Ingredient {i}: '{ingredient_data['name']}' already exists")
                        continue
                    
                    # Create ingredient
                    ingredient = Ingredient(**ingredient_data)
                    session.add(ingredient)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Ingredient {i}: Error creating ingredient: {e}")
                    logger.error(f"Error importing ingredient {i}: {e}")
            
            session.commit()
        
        return imported_count, errors


class IngredientFormatter:
    """Formats ingredient data for display."""
    
    @staticmethod
    def format_ingredient_summary(ingredient: Ingredient) -> str:
        """
        Format an ingredient for summary display.
        
        Args:
            ingredient: Ingredient object
            
        Returns:
            Formatted string
        """
        category_info = f" ({ingredient.category})" if ingredient.category else ""
        
        nutrition_parts = []
        if ingredient.calories_per_100g:
            nutrition_parts.append(f"{ingredient.calories_per_100g:.0f} cal")
        if ingredient.protein_per_100g:
            nutrition_parts.append(f"{ingredient.protein_per_100g:.1f}g protein")
        
        nutrition_info = f" - {', '.join(nutrition_parts)}" if nutrition_parts else ""
        
        return f"[{ingredient.id}] {ingredient.name}{category_info}{nutrition_info}"
    
    @staticmethod
    def format_ingredient_details(ingredient: Ingredient) -> str:
        """
        Format an ingredient for detailed display.
        
        Args:
            ingredient: Ingredient object
            
        Returns:
            Formatted string
        """
        lines = [
            f"Ingredient: {ingredient.name}",
            f"ID: {ingredient.id}",
        ]
        
        if ingredient.category:
            lines.append(f"Category: {ingredient.category}")
        
        # Nutritional information per 100g
        nutrition_lines = []
        if ingredient.calories_per_100g:
            nutrition_lines.append(f"  Calories: {ingredient.calories_per_100g:.1f}")
        if ingredient.protein_per_100g:
            nutrition_lines.append(f"  Protein: {ingredient.protein_per_100g:.1f}g")
        if ingredient.carbs_per_100g:
            nutrition_lines.append(f"  Carbs: {ingredient.carbs_per_100g:.1f}g")
        if ingredient.fat_per_100g:
            nutrition_lines.append(f"  Fat: {ingredient.fat_per_100g:.1f}g")
        if ingredient.fiber_per_100g:
            nutrition_lines.append(f"  Fiber: {ingredient.fiber_per_100g:.1f}g")
        if ingredient.sugar_per_100g:
            nutrition_lines.append(f"  Sugar: {ingredient.sugar_per_100g:.1f}g")
        if ingredient.sodium_per_100g:
            nutrition_lines.append(f"  Sodium: {ingredient.sodium_per_100g:.1f}mg")
        
        if nutrition_lines:
            lines.append("Nutrition (per 100g):")
            lines.extend(nutrition_lines)
        
        # Unit information
        if ingredient.common_unit:
            unit_info = f"Common unit: {ingredient.common_unit}"
            if ingredient.unit_weight_grams:
                unit_info += f" ({ingredient.unit_weight_grams}g)"
            lines.append(unit_info)
        
        return "\n".join(lines)
