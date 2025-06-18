"""
Calendar management functionality for the Smart Meal Planner application.

Handles calendar views, date calculations, and meal plan visualization.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from calendar import monthrange
from collections import defaultdict

from .database import get_db_session
from .models import Plan, Recipe, MealType
from .meal_planning import MealPlanner

logger = logging.getLogger(__name__)


class CalendarManager:
    """Manages calendar views and date-based meal plan operations."""
    
    @staticmethod
    def get_week_dates(target_date: date, start_on_monday: bool = True) -> Tuple[date, date]:
        """
        Get the start and end dates of the week containing the target date.
        
        Args:
            target_date: Date within the week
            start_on_monday: Whether week starts on Monday (True) or Sunday (False)
            
        Returns:
            Tuple of (start_date, end_date) for the week
        """
        if start_on_monday:
            # Monday = 0, Sunday = 6
            days_since_monday = target_date.weekday()
            start_date = target_date - timedelta(days=days_since_monday)
        else:
            # Sunday = 6, Saturday = 5 in weekday(), but we want Sunday = 0
            days_since_sunday = (target_date.weekday() + 1) % 7
            start_date = target_date - timedelta(days=days_since_sunday)
        
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    
    @staticmethod
    def get_month_dates(year: int, month: int) -> Tuple[date, date]:
        """
        Get the start and end dates of a month.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Tuple of (start_date, end_date) for the month
        """
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date
    
    @staticmethod
    def get_weekly_calendar(
        target_date: date,
        start_on_monday: bool = True,
        include_recipes: bool = True
    ) -> Dict[str, Any]:
        """
        Get a weekly calendar view with meal plans.
        
        Args:
            target_date: Date within the week to display
            start_on_monday: Whether week starts on Monday
            include_recipes: Whether to include recipe details
            
        Returns:
            Dictionary with weekly calendar data
        """
        start_date, end_date = CalendarManager.get_week_dates(target_date, start_on_monday)
        plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
        
        # Group plans by date
        plans_by_date = defaultdict(list)
        for plan in plans:
            plans_by_date[plan.date].append(plan)
        
        # Build calendar structure
        calendar_data = {
            'start_date': start_date,
            'end_date': end_date,
            'week_number': start_date.isocalendar()[1],
            'days': []
        }
        
        # Get recipe details if requested
        recipe_cache = {}
        if include_recipes and plans:
            with get_db_session() as session:
                recipe_ids = list(set(plan.recipe_id for plan in plans))
                recipes = session.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
                # Create a cache with recipe data, not objects
                for recipe in recipes:
                    recipe_cache[recipe.id] = {
                        'title': recipe.title,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time,
                        'cuisine': recipe.cuisine
                    }
        
        # Build each day
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            day_plans = plans_by_date[current_date]
            
            # Organize plans by meal type
            meals = {}
            for meal_type in MealType:
                meal_plans = [p for p in day_plans if p.meal_type == meal_type]
                meals[meal_type.value] = []
                
                for plan in meal_plans:
                    plan_data = {
                        'id': plan.id,
                        'recipe_id': plan.recipe_id,
                        'servings': plan.servings,
                        'notes': plan.notes,
                        'completed': plan.completed
                    }
                    
                    if include_recipes and plan.recipe_id in recipe_cache:
                        recipe_data = recipe_cache[plan.recipe_id]
                        plan_data['recipe'] = recipe_data
                    
                    meals[meal_type.value].append(plan_data)
            
            day_data = {
                'date': current_date,
                'day_name': current_date.strftime('%A'),
                'day_short': current_date.strftime('%a'),
                'is_today': current_date == date.today(),
                'is_weekend': current_date.weekday() >= 5,
                'meals': meals,
                'total_meals': len(day_plans),
                'completed_meals': sum(1 for p in day_plans if p.completed)
            }
            
            calendar_data['days'].append(day_data)
        
        return calendar_data
    
    @staticmethod
    def get_monthly_calendar(
        year: int,
        month: int,
        include_recipes: bool = False
    ) -> Dict[str, Any]:
        """
        Get a monthly calendar view with meal plans.
        
        Args:
            year: Year
            month: Month (1-12)
            include_recipes: Whether to include recipe details
            
        Returns:
            Dictionary with monthly calendar data
        """
        start_date, end_date = CalendarManager.get_month_dates(year, month)
        plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
        
        # Group plans by date
        plans_by_date = defaultdict(list)
        for plan in plans:
            plans_by_date[plan.date].append(plan)
        
        # Build calendar structure
        calendar_data = {
            'year': year,
            'month': month,
            'month_name': start_date.strftime('%B'),
            'start_date': start_date,
            'end_date': end_date,
            'days': []
        }
        
        # Get recipe details if requested
        recipe_cache = {}
        if include_recipes and plans:
            with get_db_session() as session:
                recipe_ids = list(set(plan.recipe_id for plan in plans))
                recipes = session.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
                # Create a cache with recipe data, not objects
                for recipe in recipes:
                    recipe_cache[recipe.id] = {
                        'title': recipe.title,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time,
                        'cuisine': recipe.cuisine
                    }
        
        # Build each day of the month
        current_date = start_date
        while current_date <= end_date:
            day_plans = plans_by_date[current_date]
            
            # Count meals by type
            meal_counts = {}
            for meal_type in MealType:
                meal_counts[meal_type.value] = sum(
                    1 for p in day_plans if p.meal_type == meal_type
                )
            
            day_data = {
                'date': current_date,
                'day': current_date.day,
                'day_name': current_date.strftime('%A'),
                'is_today': current_date == date.today(),
                'is_weekend': current_date.weekday() >= 5,
                'total_meals': len(day_plans),
                'completed_meals': sum(1 for p in day_plans if p.completed),
                'meal_counts': meal_counts
            }
            
            if include_recipes:
                # Include detailed meal information
                meals = {}
                for meal_type in MealType:
                    meal_plans = [p for p in day_plans if p.meal_type == meal_type]
                    meals[meal_type.value] = []
                    
                    for plan in meal_plans:
                        plan_data = {
                            'id': plan.id,
                            'recipe_id': plan.recipe_id,
                            'servings': plan.servings,
                            'completed': plan.completed
                        }
                        
                        if plan.recipe_id in recipe_cache:
                            recipe_data = recipe_cache[plan.recipe_id]
                            plan_data['recipe_title'] = recipe_data['title']
                        
                        meals[meal_type.value].append(plan_data)
                
                day_data['meals'] = meals
            
            calendar_data['days'].append(day_data)
            current_date += timedelta(days=1)
        
        return calendar_data
    
    @staticmethod
    def get_calendar_summary(
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get a summary of meal plans for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with calendar summary data
        """
        plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
        
        # Basic statistics
        total_days = (end_date - start_date).days + 1
        days_with_meals = len(set(plan.date for plan in plans))
        
        # Meal type distribution
        meal_type_counts = {}
        for meal_type in MealType:
            meal_type_counts[meal_type.value] = sum(
                1 for plan in plans if plan.meal_type == meal_type
            )
        
        # Completion statistics
        completed_plans = sum(1 for plan in plans if plan.completed)
        completion_rate = (completed_plans / len(plans) * 100) if plans else 0
        
        # Recipe frequency
        recipe_counts = defaultdict(int)
        for plan in plans:
            recipe_counts[plan.recipe_id] += 1
        
        # Get recipe details for most frequent
        most_frequent_recipes = []
        if recipe_counts:
            with get_db_session() as session:
                top_recipe_ids = sorted(recipe_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for recipe_id, count in top_recipe_ids:
                    recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
                    if recipe:
                        most_frequent_recipes.append({
                            'recipe_id': recipe_id,
                            'title': recipe.title,
                            'count': count
                        })
        
        # Daily averages
        avg_meals_per_day = len(plans) / total_days if total_days > 0 else 0
        
        return {
            'date_range': {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days
            },
            'meal_statistics': {
                'total_meals': len(plans),
                'days_with_meals': days_with_meals,
                'avg_meals_per_day': round(avg_meals_per_day, 1),
                'meal_type_counts': meal_type_counts
            },
            'completion_statistics': {
                'completed_meals': completed_plans,
                'completion_rate': round(completion_rate, 1)
            },
            'recipe_statistics': {
                'unique_recipes': len(recipe_counts),
                'most_frequent_recipes': most_frequent_recipes
            }
        }
    
    @staticmethod
    def find_free_meal_slots(
        start_date: date,
        end_date: date,
        meal_types: Optional[List[MealType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find available meal slots (date/meal_type combinations without plans).
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            meal_types: List of meal types to check, defaults to all
            
        Returns:
            List of available meal slots
        """
        if meal_types is None:
            meal_types = list(MealType)
        
        plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
        
        # Create set of occupied slots
        occupied_slots = set()
        for plan in plans:
            occupied_slots.add((plan.date, plan.meal_type))
        
        # Find free slots
        free_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            for meal_type in meal_types:
                if (current_date, meal_type) not in occupied_slots:
                    free_slots.append({
                        'date': current_date,
                        'meal_type': meal_type.value,
                        'day_name': current_date.strftime('%A'),
                        'is_weekend': current_date.weekday() >= 5
                    })
            
            current_date += timedelta(days=1)
        
        return free_slots
