"""
Meal planning functionality for the Smart Meal Planner application.

Handles meal scheduling, plan management, and meal plan operations.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .database import get_db_session
from .models import Plan, Recipe, MealType, create_plan

logger = logging.getLogger(__name__)


class MealPlanningError(Exception):
    """Raised when meal planning operations fail."""
    pass


class MealPlanner:
    """Handles meal planning and scheduling operations."""
    
    @staticmethod
    def schedule_meal(
        target_date: date,
        meal_type: MealType,
        recipe_id: int,
        servings: int = 1,
        notes: Optional[str] = None,
        allow_conflicts: bool = False
    ) -> Plan:
        """
        Schedule a meal for a specific date and meal type.
        
        Args:
            target_date: Date to schedule the meal
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            recipe_id: ID of the recipe to schedule
            servings: Number of servings
            notes: Optional notes for the meal plan
            allow_conflicts: Whether to allow multiple meals of same type on same date
            
        Returns:
            Created meal plan
            
        Raises:
            MealPlanningError: If recipe not found or conflicts exist
        """
        with get_db_session() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            if not recipe:
                raise MealPlanningError(f"Recipe with ID {recipe_id} not found")
            
            # Check for conflicts if not allowed
            if not allow_conflicts:
                existing_plan = session.query(Plan).filter(
                    and_(
                        Plan.date == target_date,
                        Plan.meal_type == meal_type
                    )
                ).first()
                
                if existing_plan:
                    raise MealPlanningError(
                        f"A {meal_type.value} is already scheduled for {target_date}. "
                        f"Use --allow-conflicts to override."
                    )
            
            # Create the meal plan
            plan = create_plan(
                session=session,
                date=target_date,
                meal_type=meal_type,
                recipe_id=recipe_id,
                servings=servings,
                notes=notes
            )
            
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            
            logger.info(f"Scheduled {recipe.title} for {meal_type.value} on {target_date}")
            return plan
    
    @staticmethod
    def get_meal_plan(plan_id: int) -> Optional[Plan]:
        """
        Get a meal plan by its ID.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Plan object or None if not found
        """
        with get_db_session() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                session.expunge(plan)
            return plan
    
    @staticmethod
    def update_meal_plan(
        plan_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Plan]:
        """
        Update a meal plan with new data.
        
        Args:
            plan_id: Plan ID to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated plan or None if not found
        """
        with get_db_session() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()
            
            if not plan:
                return None
            
            # Update fields
            for field, value in updates.items():
                if hasattr(plan, field):
                    if field == 'meal_type' and isinstance(value, str):
                        # Convert string to MealType enum
                        try:
                            value = MealType(value.lower())
                        except ValueError:
                            continue
                    setattr(plan, field, value)
            
            session.commit()
            session.refresh(plan)
            session.expunge(plan)
            
            logger.info(f"Updated meal plan {plan_id}")
            return plan
    
    @staticmethod
    def delete_meal_plan(plan_id: int) -> bool:
        """
        Delete a meal plan.
        
        Args:
            plan_id: Plan ID to delete
            
        Returns:
            True if plan was deleted, False if not found
        """
        with get_db_session() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()
            
            if not plan:
                return False
            
            plan_info = f"{plan.meal_type.value} on {plan.date}"
            session.delete(plan)
            session.commit()
            
            logger.info(f"Deleted meal plan: {plan_info}")
            return True
    
    @staticmethod
    def complete_meal(plan_id: int, completed: bool = True) -> Optional[Plan]:
        """
        Mark a meal plan as completed or incomplete.
        
        Args:
            plan_id: Plan ID to update
            completed: Whether the meal is completed
            
        Returns:
            Updated plan or None if not found
        """
        return MealPlanner.update_meal_plan(plan_id, {'completed': completed})
    
    @staticmethod
    def get_plans_for_date(target_date: date) -> List[Plan]:
        """
        Get all meal plans for a specific date.
        
        Args:
            target_date: Date to get plans for
            
        Returns:
            List of meal plans for the date
        """
        with get_db_session() as session:
            plans = session.query(Plan).filter(
                Plan.date == target_date
            ).order_by(Plan.meal_type).all()
            
            # Detach from session
            for plan in plans:
                session.expunge(plan)
            
            return plans
    
    @staticmethod
    def get_plans_for_date_range(
        start_date: date,
        end_date: date
    ) -> List[Plan]:
        """
        Get all meal plans within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of meal plans in the date range
        """
        with get_db_session() as session:
            plans = session.query(Plan).filter(
                and_(
                    Plan.date >= start_date,
                    Plan.date <= end_date
                )
            ).order_by(Plan.date, Plan.meal_type).all()
            
            # Detach from session
            for plan in plans:
                session.expunge(plan)
            
            return plans
    
    @staticmethod
    def clear_schedule(
        start_date: date,
        end_date: Optional[date] = None,
        meal_type: Optional[MealType] = None
    ) -> int:
        """
        Clear meal plans for a date range and/or meal type.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive), defaults to start_date
            meal_type: Optional meal type filter
            
        Returns:
            Number of plans deleted
        """
        if end_date is None:
            end_date = start_date
        
        with get_db_session() as session:
            query = session.query(Plan).filter(
                and_(
                    Plan.date >= start_date,
                    Plan.date <= end_date
                )
            )
            
            if meal_type:
                query = query.filter(Plan.meal_type == meal_type)
            
            plans = query.all()
            count = len(plans)
            
            for plan in plans:
                session.delete(plan)
            
            session.commit()
            
            logger.info(f"Cleared {count} meal plans from {start_date} to {end_date}")
            return count
    
    @staticmethod
    def plan_week(
        start_date: date,
        recipe_assignments: Dict[str, int],
        clear_existing: bool = False
    ) -> List[Plan]:
        """
        Plan meals for a week with recipe assignments.
        
        Args:
            start_date: Start date of the week (typically Monday)
            recipe_assignments: Dict mapping "day_mealtype" to recipe_id
                               e.g., {"monday_dinner": 1, "tuesday_lunch": 2}
            clear_existing: Whether to clear existing plans for the week
            
        Returns:
            List of created meal plans
        """
        end_date = start_date + timedelta(days=6)
        
        if clear_existing:
            MealPlanner.clear_schedule(start_date, end_date)
        
        created_plans = []
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day_offset, day_name in enumerate(day_names):
            current_date = start_date + timedelta(days=day_offset)
            
            for meal_type in MealType:
                key = f"{day_name}_{meal_type.value}"
                if key in recipe_assignments:
                    recipe_id = recipe_assignments[key]
                    try:
                        plan = MealPlanner.schedule_meal(
                            target_date=current_date,
                            meal_type=meal_type,
                            recipe_id=recipe_id,
                            allow_conflicts=clear_existing
                        )
                        created_plans.append(plan)
                    except MealPlanningError as e:
                        logger.warning(f"Failed to schedule {key}: {e}")
        
        return created_plans
    
    @staticmethod
    def get_meal_plan_statistics(
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get statistics for meal plans in a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with meal plan statistics
        """
        plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
        
        total_plans = len(plans)
        completed_plans = sum(1 for plan in plans if plan.completed)
        
        # Count by meal type
        meal_type_counts = {}
        for meal_type in MealType:
            meal_type_counts[meal_type.value] = sum(
                1 for plan in plans if plan.meal_type == meal_type
            )
        
        # Count by recipe
        recipe_counts = {}
        for plan in plans:
            recipe_id = plan.recipe_id
            recipe_counts[recipe_id] = recipe_counts.get(recipe_id, 0) + 1
        
        return {
            'total_plans': total_plans,
            'completed_plans': completed_plans,
            'completion_rate': (completed_plans / total_plans * 100) if total_plans > 0 else 0,
            'meal_type_counts': meal_type_counts,
            'most_planned_recipes': sorted(
                recipe_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
