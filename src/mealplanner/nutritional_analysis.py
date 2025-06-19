"""
Nutritional analysis functionality for the Smart Meal Planner application.

Handles nutrition calculations, meal plan analysis, and nutritional summaries.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .database import get_db_session
from .models import Recipe, Plan, Ingredient, recipe_ingredients
from .meal_planning import MealPlanner

logger = logging.getLogger(__name__)


@dataclass
class NutritionData:
    """Data class for nutritional information."""
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    sugar: float = 0.0
    sodium: float = 0.0
    
    def __add__(self, other: 'NutritionData') -> 'NutritionData':
        """Add two nutrition data objects."""
        return NutritionData(
            calories=self.calories + other.calories,
            protein=self.protein + other.protein,
            carbs=self.carbs + other.carbs,
            fat=self.fat + other.fat,
            fiber=self.fiber + other.fiber,
            sugar=self.sugar + other.sugar,
            sodium=self.sodium + other.sodium
        )
    
    def __mul__(self, multiplier: float) -> 'NutritionData':
        """Multiply nutrition data by a factor."""
        return NutritionData(
            calories=self.calories * multiplier,
            protein=self.protein * multiplier,
            carbs=self.carbs * multiplier,
            fat=self.fat * multiplier,
            fiber=self.fiber * multiplier,
            sugar=self.sugar * multiplier,
            sodium=self.sodium * multiplier
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'calories': round(self.calories, 1),
            'protein': round(self.protein, 1),
            'carbs': round(self.carbs, 1),
            'fat': round(self.fat, 1),
            'fiber': round(self.fiber, 1),
            'sugar': round(self.sugar, 1),
            'sodium': round(self.sodium, 1)
        }


class NutritionalAnalyzer:
    """Handles nutritional analysis calculations and summaries."""
    
    @staticmethod
    def analyze_recipe(recipe_id: int, servings: int = 1) -> Optional[NutritionData]:
        """
        Analyze the nutritional content of a recipe.
        
        Args:
            recipe_id: Recipe ID to analyze
            servings: Number of servings to calculate for
            
        Returns:
            NutritionData object or None if recipe not found
        """
        with get_db_session() as session:
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            if not recipe:
                return None
            
            # Start with recipe's own nutritional data (per serving)
            nutrition = NutritionData(
                calories=recipe.calories or 0.0,
                protein=recipe.protein or 0.0,
                carbs=recipe.carbs or 0.0,
                fat=recipe.fat or 0.0,
                fiber=recipe.fiber or 0.0,
                sugar=recipe.sugar or 0.0,
                sodium=recipe.sodium or 0.0
            )
            
            # If recipe has no nutritional data, calculate from ingredients
            if nutrition.calories == 0 and recipe.ingredients:
                ingredient_nutrition = NutritionalAnalyzer._calculate_from_ingredients(
                    session, recipe_id, recipe.servings or 1
                )
                if ingredient_nutrition:
                    nutrition = ingredient_nutrition
            
            # Scale by requested servings
            if servings != 1:
                nutrition = nutrition * servings
            
            return nutrition
    
    @staticmethod
    def _calculate_from_ingredients(
        session, 
        recipe_id: int, 
        recipe_servings: int
    ) -> Optional[NutritionData]:
        """
        Calculate nutrition from recipe ingredients.
        
        Args:
            session: Database session
            recipe_id: Recipe ID
            recipe_servings: Number of servings the recipe makes
            
        Returns:
            NutritionData per serving or None if no ingredient data
        """
        # Get recipe ingredients with quantities
        ingredient_data = session.query(
            Ingredient,
            recipe_ingredients.c.quantity,
            recipe_ingredients.c.unit
        ).join(
            recipe_ingredients, Ingredient.id == recipe_ingredients.c.ingredient_id
        ).filter(
            recipe_ingredients.c.recipe_id == recipe_id
        ).all()
        
        if not ingredient_data:
            return None
        
        total_nutrition = NutritionData()
        
        for ingredient, quantity, unit in ingredient_data:
            if not quantity or not ingredient.calories_per_100g:
                continue
            
            # Convert quantity to grams (simplified - assumes quantity is in grams)
            # In a real implementation, you'd have unit conversion logic
            quantity_grams = float(quantity)
            
            # Calculate nutrition for this ingredient quantity
            ingredient_nutrition = NutritionData(
                calories=ingredient.calories_per_100g or 0.0,
                protein=ingredient.protein_per_100g or 0.0,
                carbs=ingredient.carbs_per_100g or 0.0,
                fat=ingredient.fat_per_100g or 0.0,
                fiber=ingredient.fiber_per_100g or 0.0,
                sugar=ingredient.sugar_per_100g or 0.0,
                sodium=ingredient.sodium_per_100g or 0.0
            )
            
            # Scale by quantity (per 100g to actual quantity)
            scaled_nutrition = ingredient_nutrition * (quantity_grams / 100.0)
            total_nutrition = total_nutrition + scaled_nutrition
        
        # Return per serving
        if recipe_servings > 0:
            return total_nutrition * (1.0 / recipe_servings)
        
        return total_nutrition
    
    @staticmethod
    def analyze_meal_plan(plan_id: int) -> Optional[NutritionData]:
        """
        Analyze the nutritional content of a meal plan.
        
        Args:
            plan_id: Meal plan ID to analyze
            
        Returns:
            NutritionData object or None if plan not found
        """
        with get_db_session() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                return None
            
            return NutritionalAnalyzer.analyze_recipe(plan.recipe_id, plan.servings)
    
    @staticmethod
    def analyze_daily_nutrition(target_date: date) -> Dict[str, Any]:
        """
        Analyze nutritional content for all meals on a specific date.
        
        Args:
            target_date: Date to analyze
            
        Returns:
            Dictionary with daily nutrition analysis
        """
        plans = MealPlanner.get_plans_for_date(target_date)
        
        total_nutrition = NutritionData()
        meal_nutrition = {}
        
        for plan in plans:
            plan_nutrition = NutritionalAnalyzer.analyze_meal_plan(plan.id)
            if plan_nutrition:
                total_nutrition = total_nutrition + plan_nutrition
                meal_nutrition[plan.meal_type.value] = plan_nutrition.to_dict()
        
        return {
            'date': target_date,
            'total_nutrition': total_nutrition.to_dict(),
            'meal_nutrition': meal_nutrition,
            'meal_count': len(plans),
            'completed_meals': sum(1 for plan in plans if plan.completed)
        }
    
    @staticmethod
    def analyze_period_nutrition(
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Analyze nutritional content for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with period nutrition analysis
        """
        daily_analyses = []
        total_nutrition = NutritionData()
        meal_type_totals = defaultdict(lambda: NutritionData())
        
        current_date = start_date
        while current_date <= end_date:
            daily_analysis = NutritionalAnalyzer.analyze_daily_nutrition(current_date)
            daily_analyses.append(daily_analysis)
            
            # Add to totals
            daily_total = NutritionData(**daily_analysis['total_nutrition'])
            total_nutrition = total_nutrition + daily_total
            
            # Add to meal type totals
            for meal_type, nutrition in daily_analysis['meal_nutrition'].items():
                meal_nutrition = NutritionData(**nutrition)
                meal_type_totals[meal_type] = meal_type_totals[meal_type] + meal_nutrition
            
            current_date += timedelta(days=1)
        
        # Calculate averages
        total_days = (end_date - start_date).days + 1
        avg_nutrition = total_nutrition * (1.0 / total_days) if total_days > 0 else NutritionData()
        
        # Convert meal type totals to dict
        meal_type_dict = {
            meal_type: nutrition.to_dict() 
            for meal_type, nutrition in meal_type_totals.items()
        }
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'total_nutrition': total_nutrition.to_dict(),
            'average_daily_nutrition': avg_nutrition.to_dict(),
            'meal_type_totals': meal_type_dict,
            'daily_analyses': daily_analyses
        }
    
    @staticmethod
    def calculate_macro_ratios(nutrition: NutritionData) -> Dict[str, float]:
        """
        Calculate macronutrient ratios from nutrition data.
        
        Args:
            nutrition: NutritionData object
            
        Returns:
            Dictionary with macro ratios as percentages
        """
        # Calculate calories from macros (4 cal/g protein, 4 cal/g carbs, 9 cal/g fat)
        protein_calories = nutrition.protein * 4
        carb_calories = nutrition.carbs * 4
        fat_calories = nutrition.fat * 9
        
        total_macro_calories = protein_calories + carb_calories + fat_calories
        
        if total_macro_calories == 0:
            return {'protein': 0.0, 'carbs': 0.0, 'fat': 0.0}
        
        return {
            'protein': round((protein_calories / total_macro_calories) * 100, 1),
            'carbs': round((carb_calories / total_macro_calories) * 100, 1),
            'fat': round((fat_calories / total_macro_calories) * 100, 1)
        }
    
    @staticmethod
    def assess_nutritional_balance(nutrition: NutritionData) -> Dict[str, Any]:
        """
        Assess the nutritional balance of a nutrition profile.
        
        Args:
            nutrition: NutritionData object
            
        Returns:
            Dictionary with balance assessment
        """
        macro_ratios = NutritionalAnalyzer.calculate_macro_ratios(nutrition)
        
        # Define healthy ranges (these are general guidelines)
        healthy_ranges = {
            'protein': (10, 35),  # 10-35% of calories
            'carbs': (45, 65),    # 45-65% of calories
            'fat': (20, 35)       # 20-35% of calories
        }
        
        balance_score = 0
        recommendations = []
        
        for macro, ratio in macro_ratios.items():
            min_range, max_range = healthy_ranges[macro]
            
            if min_range <= ratio <= max_range:
                balance_score += 1
            elif ratio < min_range:
                recommendations.append(f"Consider increasing {macro} intake (currently {ratio}%, recommended {min_range}-{max_range}%)")
            else:
                recommendations.append(f"Consider reducing {macro} intake (currently {ratio}%, recommended {min_range}-{max_range}%)")
        
        # Fiber assessment (recommended 25-35g per day for adults)
        if nutrition.fiber < 25:
            recommendations.append(f"Consider increasing fiber intake (currently {nutrition.fiber}g, recommended 25-35g)")
        
        # Sodium assessment (recommended <2300mg per day)
        if nutrition.sodium > 2300:
            recommendations.append(f"Consider reducing sodium intake (currently {nutrition.sodium}mg, recommended <2300mg)")
        
        return {
            'macro_ratios': macro_ratios,
            'balance_score': balance_score,
            'max_score': 3,
            'balance_percentage': round((balance_score / 3) * 100, 1),
            'recommendations': recommendations
        }
