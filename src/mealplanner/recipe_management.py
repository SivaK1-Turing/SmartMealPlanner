"""
Recipe management functionality for the Smart Meal Planner application.

Handles CRUD operations, searching, filtering, and pagination for recipes.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from .database import get_db_session
from .models import Recipe, Plan

logger = logging.getLogger(__name__)


class RecipeManager:
    """Manages recipe CRUD operations and queries."""
    
    @staticmethod
    def get_recipe_by_id(recipe_id: int) -> Optional[Recipe]:
        """
        Get a recipe by its ID.

        Args:
            recipe_id: Recipe ID

        Returns:
            Recipe object or None if not found
        """
        with get_db_session() as session:
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            if recipe:
                session.expunge(recipe)
            return recipe
    
    @staticmethod
    def list_recipes(
        page: int = 1,
        per_page: int = 10,
        cuisine: Optional[str] = None,
        max_time: Optional[int] = None,
        diet: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = 'title'
    ) -> Tuple[List[Recipe], int, int]:
        """
        List recipes with filtering, pagination, and sorting.

        Args:
            page: Page number (1-based)
            per_page: Number of recipes per page
            cuisine: Filter by cuisine
            max_time: Maximum total cooking time in minutes
            diet: Filter by dietary tag
            search: Search term for title and description
            sort_by: Sort field ('title', 'prep_time', 'created_at')

        Returns:
            Tuple of (recipes, total_count, total_pages)
        """
        with get_db_session() as session:
            query = session.query(Recipe)

            # Apply filters
            if cuisine:
                query = query.filter(Recipe.cuisine.ilike(f"%{cuisine}%"))

            if max_time:
                # Filter by total time (prep_time + cook_time)
                query = query.filter(
                    or_(
                        and_(Recipe.prep_time.isnot(None), Recipe.cook_time.isnot(None),
                             Recipe.prep_time + Recipe.cook_time <= max_time),
                        and_(Recipe.prep_time.isnot(None), Recipe.cook_time.is_(None),
                             Recipe.prep_time <= max_time),
                        and_(Recipe.prep_time.is_(None), Recipe.cook_time.isnot(None),
                             Recipe.cook_time <= max_time)
                    )
                )

            if diet:
                query = query.filter(Recipe.dietary_tags.ilike(f"%{diet}%"))

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Recipe.title.ilike(search_term),
                        Recipe.description.ilike(search_term),
                        Recipe.instructions.ilike(search_term)
                    )
                )

            # Apply sorting
            if sort_by == 'prep_time':
                query = query.order_by(Recipe.prep_time.asc().nulls_last())
            elif sort_by == 'created_at':
                query = query.order_by(Recipe.created_at.desc())
            else:  # Default to title
                query = query.order_by(Recipe.title.asc())

            # Get total count
            total_count = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            recipes = query.offset(offset).limit(per_page).all()

            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page

            # Detach recipes from session to avoid lazy loading issues
            for recipe in recipes:
                session.expunge(recipe)

            return recipes, total_count, total_pages
    
    @staticmethod
    def search_recipes(
        search_term: str,
        page: int = 1,
        per_page: int = 10
    ) -> Tuple[List[Recipe], int, int]:
        """
        Search recipes by title, description, and instructions.
        
        Args:
            search_term: Search term
            page: Page number (1-based)
            per_page: Number of recipes per page
            
        Returns:
            Tuple of (recipes, total_count, total_pages)
        """
        return RecipeManager.list_recipes(
            page=page,
            per_page=per_page,
            search=search_term
        )
    
    @staticmethod
    def update_recipe(recipe_id: int, updates: Dict[str, Any]) -> Optional[Recipe]:
        """
        Update a recipe with new data.
        
        Args:
            recipe_id: Recipe ID to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated recipe or None if not found
        """
        with get_db_session() as session:
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            
            if not recipe:
                return None
            
            # Update fields
            for field, value in updates.items():
                if hasattr(recipe, field):
                    if field == 'dietary_tags' and isinstance(value, list):
                        recipe.set_dietary_tags_list(value)
                    else:
                        setattr(recipe, field, value)
            
            session.commit()
            logger.info(f"Updated recipe: {recipe.title}")
            return recipe
    
    @staticmethod
    def delete_recipe(recipe_id: int) -> bool:
        """
        Delete a recipe and its associated plans.
        
        Args:
            recipe_id: Recipe ID to delete
            
        Returns:
            True if recipe was deleted, False if not found
        """
        with get_db_session() as session:
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            
            if not recipe:
                return False
            
            # Check for associated plans
            plan_count = session.query(Plan).filter(Plan.recipe_id == recipe_id).count()
            
            recipe_title = recipe.title
            session.delete(recipe)
            session.commit()
            
            logger.info(f"Deleted recipe: {recipe_title} (had {plan_count} associated plans)")
            return True
    
    @staticmethod
    def get_recipe_statistics() -> Dict[str, Any]:
        """
        Get statistics about recipes in the database.
        
        Returns:
            Dictionary with recipe statistics
        """
        with get_db_session() as session:
            total_recipes = session.query(Recipe).count()
            
            # Count by cuisine
            cuisine_counts = session.query(
                Recipe.cuisine,
                func.count(Recipe.id).label('count')
            ).filter(Recipe.cuisine.isnot(None)).group_by(Recipe.cuisine).all()
            
            # Average times
            avg_prep_time = session.query(func.avg(Recipe.prep_time)).filter(
                Recipe.prep_time.isnot(None)
            ).scalar()
            
            avg_cook_time = session.query(func.avg(Recipe.cook_time)).filter(
                Recipe.cook_time.isnot(None)
            ).scalar()
            
            return {
                'total_recipes': total_recipes,
                'cuisines': dict(cuisine_counts),
                'avg_prep_time': round(avg_prep_time, 1) if avg_prep_time else None,
                'avg_cook_time': round(avg_cook_time, 1) if avg_cook_time else None
            }
    
    @staticmethod
    def get_recipes_by_cuisine(cuisine: str) -> List[Recipe]:
        """
        Get all recipes for a specific cuisine.
        
        Args:
            cuisine: Cuisine name
            
        Returns:
            List of recipes
        """
        with get_db_session() as session:
            return session.query(Recipe).filter(
                Recipe.cuisine.ilike(f"%{cuisine}%")
            ).order_by(Recipe.title).all()
    
    @staticmethod
    def get_recipes_by_dietary_tag(tag: str) -> List[Recipe]:
        """
        Get all recipes with a specific dietary tag.
        
        Args:
            tag: Dietary tag
            
        Returns:
            List of recipes
        """
        with get_db_session() as session:
            return session.query(Recipe).filter(
                Recipe.dietary_tags.ilike(f"%{tag}%")
            ).order_by(Recipe.title).all()
    
    @staticmethod
    def get_quick_recipes(max_time: int = 30) -> List[Recipe]:
        """
        Get recipes that can be prepared quickly.
        
        Args:
            max_time: Maximum total time in minutes
            
        Returns:
            List of quick recipes
        """
        with get_db_session() as session:
            return session.query(Recipe).filter(
                or_(
                    and_(Recipe.prep_time.isnot(None), Recipe.cook_time.isnot(None),
                         Recipe.prep_time + Recipe.cook_time <= max_time),
                    and_(Recipe.prep_time.isnot(None), Recipe.cook_time.is_(None),
                         Recipe.prep_time <= max_time),
                    and_(Recipe.prep_time.is_(None), Recipe.cook_time.isnot(None),
                         Recipe.cook_time <= max_time)
                )
            ).order_by(
                (Recipe.prep_time + Recipe.cook_time).asc().nulls_last()
            ).all()


class RecipeFormatter:
    """Formats recipe data for display."""
    
    @staticmethod
    def format_recipe_summary(recipe: Recipe) -> str:
        """
        Format a recipe for summary display.
        
        Args:
            recipe: Recipe object
            
        Returns:
            Formatted string
        """
        time_info = ""
        if recipe.total_time:
            time_info = f" ({recipe.total_time} min)"
        elif recipe.prep_time:
            time_info = f" (prep: {recipe.prep_time} min)"
        elif recipe.cook_time:
            time_info = f" (cook: {recipe.cook_time} min)"
        
        cuisine_info = f" - {recipe.cuisine}" if recipe.cuisine else ""
        
        return f"[{recipe.id}] {recipe.title}{time_info}{cuisine_info}"
    
    @staticmethod
    def format_recipe_details(recipe: Recipe) -> str:
        """
        Format a recipe for detailed display.
        
        Args:
            recipe: Recipe object
            
        Returns:
            Formatted string
        """
        lines = [
            f"Recipe: {recipe.title}",
            f"ID: {recipe.id}",
        ]
        
        if recipe.description:
            lines.append(f"Description: {recipe.description}")
        
        if recipe.cuisine:
            lines.append(f"Cuisine: {recipe.cuisine}")
        
        if recipe.servings:
            lines.append(f"Servings: {recipe.servings}")
        
        # Time information
        time_parts = []
        if recipe.prep_time:
            time_parts.append(f"Prep: {recipe.prep_time} min")
        if recipe.cook_time:
            time_parts.append(f"Cook: {recipe.cook_time} min")
        if recipe.total_time:
            time_parts.append(f"Total: {recipe.total_time} min")
        
        if time_parts:
            lines.append(f"Time: {', '.join(time_parts)}")
        
        # Nutritional information
        nutrition_parts = []
        if recipe.calories:
            nutrition_parts.append(f"Calories: {recipe.calories}")
        if recipe.protein:
            nutrition_parts.append(f"Protein: {recipe.protein}g")
        if recipe.carbs:
            nutrition_parts.append(f"Carbs: {recipe.carbs}g")
        if recipe.fat:
            nutrition_parts.append(f"Fat: {recipe.fat}g")
        
        if nutrition_parts:
            lines.append(f"Nutrition: {', '.join(nutrition_parts)}")
        
        # Dietary tags
        dietary_tags = recipe.get_dietary_tags_list()
        if dietary_tags:
            lines.append(f"Dietary Tags: {', '.join(dietary_tags)}")
        
        if recipe.instructions:
            lines.append(f"Instructions: {recipe.instructions}")
        
        if recipe.source_url:
            lines.append(f"Source: {recipe.source_url}")
        
        return "\n".join(lines)
