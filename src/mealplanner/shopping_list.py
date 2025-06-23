"""
Shopping list functionality for the Smart Meal Planner application.

Handles ingredient aggregation, quantity calculations, and shopping list generation.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from .database import get_db_session
from .models import Recipe, Plan, Ingredient, recipe_ingredients
from .meal_planning import MealPlanner

logger = logging.getLogger(__name__)


@dataclass
class ShoppingListItem:
    """Data class for shopping list items."""
    ingredient_id: int
    ingredient_name: str
    category: Optional[str]
    total_quantity: float
    unit: str
    recipes_used: List[str]  # List of recipe names using this ingredient
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient_name,
            'category': self.category,
            'total_quantity': round(self.total_quantity, 2),
            'unit': self.unit,
            'recipes_used': self.recipes_used,
            'notes': self.notes
        }


@dataclass
class ShoppingList:
    """Data class for complete shopping lists."""
    start_date: date
    end_date: date
    items: List[ShoppingListItem]
    total_recipes: int
    total_meals: int
    categories: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'items': [item.to_dict() for item in self.items],
            'total_recipes': self.total_recipes,
            'total_meals': self.total_meals,
            'categories': self.categories,
            'total_items': len(self.items)
        }


class ShoppingListGenerator:
    """Generates shopping lists from meal plans."""
    
    @staticmethod
    def generate_from_date_range(
        start_date: date,
        end_date: date,
        group_by_category: bool = True,
        include_completed: bool = False
    ) -> ShoppingList:
        """
        Generate a shopping list from meal plans in a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            group_by_category: Whether to group items by category
            include_completed: Whether to include completed meals
            
        Returns:
            ShoppingList object
        """
        with get_db_session() as session:
            # Get all meal plans in the date range
            query = session.query(Plan).filter(
                Plan.date >= start_date,
                Plan.date <= end_date
            )
            
            if not include_completed:
                query = query.filter(Plan.completed == False)
            
            plans = query.all()
            
            if not plans:
                return ShoppingList(
                    start_date=start_date,
                    end_date=end_date,
                    items=[],
                    total_recipes=0,
                    total_meals=0,
                    categories=[]
                )
            
            # Aggregate ingredients from all plans
            ingredient_aggregation = defaultdict(lambda: {
                'total_quantity': 0.0,
                'unit': '',
                'recipes': set(),
                'ingredient': None
            })
            
            recipe_ids = set()
            
            for plan in plans:
                recipe_ids.add(plan.recipe_id)
                
                # Get recipe ingredients
                recipe_ingredients_data = session.query(
                    Ingredient,
                    recipe_ingredients.c.quantity,
                    recipe_ingredients.c.unit,
                    Recipe.title
                ).join(
                    recipe_ingredients, Ingredient.id == recipe_ingredients.c.ingredient_id
                ).join(
                    Recipe, Recipe.id == recipe_ingredients.c.recipe_id
                ).filter(
                    recipe_ingredients.c.recipe_id == plan.recipe_id
                ).all()
                
                for ingredient, quantity, unit, recipe_title in recipe_ingredients_data:
                    if quantity is None:
                        continue
                    
                    # Scale quantity by servings
                    scaled_quantity = float(quantity) * plan.servings
                    
                    # Aggregate by ingredient
                    key = ingredient.id
                    agg = ingredient_aggregation[key]
                    
                    if agg['ingredient'] is None:
                        agg['ingredient'] = ingredient
                        agg['unit'] = unit or 'units'
                    
                    # Add quantity (assuming same units for now)
                    agg['total_quantity'] += scaled_quantity
                    agg['recipes'].add(recipe_title)
            
            # Convert aggregation to shopping list items
            items = []
            categories = set()
            
            for ingredient_id, agg in ingredient_aggregation.items():
                ingredient = agg['ingredient']
                if ingredient.category:
                    categories.add(ingredient.category)
                
                item = ShoppingListItem(
                    ingredient_id=ingredient.id,
                    ingredient_name=ingredient.name,
                    category=ingredient.category,
                    total_quantity=agg['total_quantity'],
                    unit=agg['unit'],
                    recipes_used=sorted(list(agg['recipes']))
                )
                items.append(item)
            
            # Sort items
            if group_by_category:
                items.sort(key=lambda x: (x.category or 'ZZZ', x.ingredient_name))
            else:
                items.sort(key=lambda x: x.ingredient_name)
            
            return ShoppingList(
                start_date=start_date,
                end_date=end_date,
                items=items,
                total_recipes=len(recipe_ids),
                total_meals=len(plans),
                categories=sorted(list(categories))
            )
    
    @staticmethod
    def generate_from_recipes(
        recipe_ids: List[int],
        servings_per_recipe: Optional[Dict[int, int]] = None
    ) -> ShoppingList:
        """
        Generate a shopping list from specific recipes.
        
        Args:
            recipe_ids: List of recipe IDs
            servings_per_recipe: Optional dict mapping recipe_id to servings
            
        Returns:
            ShoppingList object
        """
        if not recipe_ids:
            return ShoppingList(
                start_date=date.today(),
                end_date=date.today(),
                items=[],
                total_recipes=0,
                total_meals=0,
                categories=[]
            )
        
        servings_per_recipe = servings_per_recipe or {}
        
        with get_db_session() as session:
            # Aggregate ingredients from recipes
            ingredient_aggregation = defaultdict(lambda: {
                'total_quantity': 0.0,
                'unit': '',
                'recipes': set(),
                'ingredient': None
            })
            
            for recipe_id in recipe_ids:
                servings = servings_per_recipe.get(recipe_id, 1)
                
                # Get recipe ingredients
                recipe_ingredients_data = session.query(
                    Ingredient,
                    recipe_ingredients.c.quantity,
                    recipe_ingredients.c.unit,
                    Recipe.title
                ).join(
                    recipe_ingredients, Ingredient.id == recipe_ingredients.c.ingredient_id
                ).join(
                    Recipe, Recipe.id == recipe_ingredients.c.recipe_id
                ).filter(
                    recipe_ingredients.c.recipe_id == recipe_id
                ).all()
                
                for ingredient, quantity, unit, recipe_title in recipe_ingredients_data:
                    if quantity is None:
                        continue
                    
                    # Scale quantity by servings
                    scaled_quantity = float(quantity) * servings
                    
                    # Aggregate by ingredient
                    key = ingredient.id
                    agg = ingredient_aggregation[key]
                    
                    if agg['ingredient'] is None:
                        agg['ingredient'] = ingredient
                        agg['unit'] = unit or 'units'
                    
                    # Add quantity
                    agg['total_quantity'] += scaled_quantity
                    agg['recipes'].add(recipe_title)
            
            # Convert to shopping list items
            items = []
            categories = set()
            
            for ingredient_id, agg in ingredient_aggregation.items():
                ingredient = agg['ingredient']
                if ingredient.category:
                    categories.add(ingredient.category)
                
                item = ShoppingListItem(
                    ingredient_id=ingredient.id,
                    ingredient_name=ingredient.name,
                    category=ingredient.category,
                    total_quantity=agg['total_quantity'],
                    unit=agg['unit'],
                    recipes_used=sorted(list(agg['recipes']))
                )
                items.append(item)
            
            # Sort by category then name
            items.sort(key=lambda x: (x.category or 'ZZZ', x.ingredient_name))
            
            return ShoppingList(
                start_date=date.today(),
                end_date=date.today(),
                items=items,
                total_recipes=len(recipe_ids),
                total_meals=len(recipe_ids),  # Each recipe counts as one meal
                categories=sorted(list(categories))
            )
    
    @staticmethod
    def add_custom_item(
        shopping_list: ShoppingList,
        item_name: str,
        quantity: float,
        unit: str,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ShoppingList:
        """
        Add a custom item to an existing shopping list.
        
        Args:
            shopping_list: Existing shopping list
            item_name: Name of the custom item
            quantity: Quantity needed
            unit: Unit of measurement
            category: Optional category
            notes: Optional notes
            
        Returns:
            Updated shopping list
        """
        custom_item = ShoppingListItem(
            ingredient_id=-1,  # Use -1 for custom items
            ingredient_name=item_name,
            category=category,
            total_quantity=quantity,
            unit=unit,
            recipes_used=[],
            notes=notes
        )
        
        # Add to items list
        new_items = shopping_list.items + [custom_item]
        
        # Update categories if new category
        new_categories = shopping_list.categories.copy()
        if category and category not in new_categories:
            new_categories.append(category)
            new_categories.sort()
        
        # Sort items again
        new_items.sort(key=lambda x: (x.category or 'ZZZ', x.ingredient_name))
        
        return ShoppingList(
            start_date=shopping_list.start_date,
            end_date=shopping_list.end_date,
            items=new_items,
            total_recipes=shopping_list.total_recipes,
            total_meals=shopping_list.total_meals,
            categories=new_categories
        )
    
    @staticmethod
    def calculate_shopping_list_nutrition(shopping_list: ShoppingList) -> Dict[str, float]:
        """
        Calculate approximate nutritional content of a shopping list.
        
        Args:
            shopping_list: Shopping list to analyze
            
        Returns:
            Dictionary with nutritional totals
        """
        total_nutrition = {
            'calories': 0.0,
            'protein': 0.0,
            'carbs': 0.0,
            'fat': 0.0,
            'fiber': 0.0,
            'sodium': 0.0
        }
        
        with get_db_session() as session:
            for item in shopping_list.items:
                if item.ingredient_id == -1:  # Skip custom items
                    continue
                
                ingredient = session.query(Ingredient).filter(
                    Ingredient.id == item.ingredient_id
                ).first()
                
                if not ingredient:
                    continue
                
                # Calculate nutrition based on quantity (assuming grams)
                # This is a simplified calculation - in reality you'd need unit conversion
                quantity_factor = item.total_quantity / 100.0  # Convert to per-100g basis
                
                if ingredient.calories_per_100g:
                    total_nutrition['calories'] += ingredient.calories_per_100g * quantity_factor
                if ingredient.protein_per_100g:
                    total_nutrition['protein'] += ingredient.protein_per_100g * quantity_factor
                if ingredient.carbs_per_100g:
                    total_nutrition['carbs'] += ingredient.carbs_per_100g * quantity_factor
                if ingredient.fat_per_100g:
                    total_nutrition['fat'] += ingredient.fat_per_100g * quantity_factor
                if ingredient.fiber_per_100g:
                    total_nutrition['fiber'] += ingredient.fiber_per_100g * quantity_factor
                if ingredient.sodium_per_100g:
                    total_nutrition['sodium'] += ingredient.sodium_per_100g * quantity_factor
        
        # Round values
        return {k: round(v, 1) for k, v in total_nutrition.items()}
