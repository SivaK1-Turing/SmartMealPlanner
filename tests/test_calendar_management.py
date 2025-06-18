"""
Tests for the calendar management module.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from mealplanner.models import Recipe, Plan, MealType
from mealplanner.calendar_management import CalendarManager


class TestCalendarManager:
    """Test the CalendarManager class."""
    
    def test_get_week_dates_monday_start(self):
        """Test getting week dates starting on Monday."""
        # Test with a Wednesday (2024-01-03 is a Wednesday)
        target_date = date(2024, 1, 3)
        start_date, end_date = CalendarManager.get_week_dates(target_date, start_on_monday=True)
        
        # Should start on Monday (2024-01-01) and end on Sunday (2024-01-07)
        assert start_date == date(2024, 1, 1)
        assert end_date == date(2024, 1, 7)
    
    def test_get_week_dates_sunday_start(self):
        """Test getting week dates starting on Sunday."""
        # Test with a Wednesday (2024-01-03 is a Wednesday)
        target_date = date(2024, 1, 3)
        start_date, end_date = CalendarManager.get_week_dates(target_date, start_on_monday=False)
        
        # Should start on Sunday (2023-12-31) and end on Saturday (2024-01-06)
        assert start_date == date(2023, 12, 31)
        assert end_date == date(2024, 1, 6)
    
    def test_get_month_dates(self):
        """Test getting month dates."""
        start_date, end_date = CalendarManager.get_month_dates(2024, 2)  # February 2024
        
        assert start_date == date(2024, 2, 1)
        assert end_date == date(2024, 2, 29)  # 2024 is a leap year
    
    def test_get_month_dates_non_leap_year(self):
        """Test getting month dates for non-leap year."""
        start_date, end_date = CalendarManager.get_month_dates(2023, 2)  # February 2023
        
        assert start_date == date(2023, 2, 1)
        assert end_date == date(2023, 2, 28)  # 2023 is not a leap year
    
    def test_get_weekly_calendar_basic(self):
        """Test getting basic weekly calendar without recipes."""
        target_date = date(2024, 1, 3)  # Wednesday
        
        # Mock meal plans
        mock_plans = [
            Plan(
                id=1,
                date=date(2024, 1, 1),  # Monday
                meal_type=MealType.BREAKFAST,
                recipe_id=1,
                servings=2,
                completed=False
            ),
            Plan(
                id=2,
                date=date(2024, 1, 2),  # Tuesday
                meal_type=MealType.LUNCH,
                recipe_id=2,
                servings=1,
                completed=True
            )
        ]
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = mock_plans
            
            calendar_data = CalendarManager.get_weekly_calendar(
                target_date=target_date,
                include_recipes=False
            )
            
            assert calendar_data['start_date'] == date(2024, 1, 1)
            assert calendar_data['end_date'] == date(2024, 1, 7)
            assert calendar_data['week_number'] == 1
            assert len(calendar_data['days']) == 7
            
            # Check Monday has breakfast
            monday = calendar_data['days'][0]
            assert monday['date'] == date(2024, 1, 1)
            assert monday['day_name'] == 'Monday'
            assert monday['total_meals'] == 1
            assert monday['completed_meals'] == 0
            assert len(monday['meals']['breakfast']) == 1
            
            # Check Tuesday has lunch
            tuesday = calendar_data['days'][1]
            assert tuesday['date'] == date(2024, 1, 2)
            assert tuesday['total_meals'] == 1
            assert tuesday['completed_meals'] == 1
            assert len(tuesday['meals']['lunch']) == 1
    
    def test_get_weekly_calendar_with_recipes(self):
        """Test getting weekly calendar with recipe details."""
        target_date = date(2024, 1, 3)
        
        # Mock meal plans
        mock_plans = [
            Plan(
                id=1,
                date=date(2024, 1, 1),
                meal_type=MealType.DINNER,
                recipe_id=1,
                servings=2,
                completed=False
            )
        ]
        
        # Mock recipes
        mock_recipes = [
            Recipe(
                id=1,
                title="Chicken Stir Fry",
                prep_time=15,
                cook_time=10,
                cuisine="Asian"
            )
        ]
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans, \
             patch('mealplanner.calendar_management.get_db_session') as mock_session:
            
            mock_get_plans.return_value = mock_plans
            
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.all.return_value = mock_recipes
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            calendar_data = CalendarManager.get_weekly_calendar(
                target_date=target_date,
                include_recipes=True
            )
            
            # Check recipe details are included
            monday = calendar_data['days'][0]
            dinner_plan = monday['meals']['dinner'][0]
            assert 'recipe' in dinner_plan
            assert dinner_plan['recipe']['title'] == "Chicken Stir Fry"
            assert dinner_plan['recipe']['cuisine'] == "Asian"
    
    def test_get_monthly_calendar_basic(self):
        """Test getting basic monthly calendar."""
        # Mock meal plans
        mock_plans = [
            Plan(
                id=1,
                date=date(2024, 2, 1),
                meal_type=MealType.BREAKFAST,
                recipe_id=1,
                servings=1,
                completed=True
            ),
            Plan(
                id=2,
                date=date(2024, 2, 1),
                meal_type=MealType.LUNCH,
                recipe_id=2,
                servings=1,
                completed=False
            )
        ]
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = mock_plans
            
            calendar_data = CalendarManager.get_monthly_calendar(
                year=2024,
                month=2,
                include_recipes=False
            )
            
            assert calendar_data['year'] == 2024
            assert calendar_data['month'] == 2
            assert calendar_data['month_name'] == 'February'
            assert calendar_data['start_date'] == date(2024, 2, 1)
            assert calendar_data['end_date'] == date(2024, 2, 29)
            assert len(calendar_data['days']) == 29  # February 2024 has 29 days
            
            # Check first day
            first_day = calendar_data['days'][0]
            assert first_day['date'] == date(2024, 2, 1)
            assert first_day['day'] == 1
            assert first_day['total_meals'] == 2
            assert first_day['completed_meals'] == 1
            assert first_day['meal_counts']['breakfast'] == 1
            assert first_day['meal_counts']['lunch'] == 1
    
    def test_get_calendar_summary(self):
        """Test getting calendar summary."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)
        
        # Mock meal plans
        mock_plans = [
            Plan(id=1, date=date(2024, 1, 1), meal_type=MealType.BREAKFAST, recipe_id=1, completed=True),
            Plan(id=2, date=date(2024, 1, 1), meal_type=MealType.LUNCH, recipe_id=2, completed=False),
            Plan(id=3, date=date(2024, 1, 2), meal_type=MealType.DINNER, recipe_id=1, completed=True),
            Plan(id=4, date=date(2024, 1, 3), meal_type=MealType.BREAKFAST, recipe_id=3, completed=False)
        ]
        
        # Mock recipes
        mock_recipes = [
            Recipe(id=1, title="Recipe 1"),
            Recipe(id=2, title="Recipe 2"),
            Recipe(id=3, title="Recipe 3")
        ]
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans, \
             patch('mealplanner.calendar_management.get_db_session') as mock_session:
            
            mock_get_plans.return_value = mock_plans
            
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.side_effect = mock_recipes
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            summary = CalendarManager.get_calendar_summary(start_date, end_date)
            
            assert summary['date_range']['start_date'] == start_date
            assert summary['date_range']['end_date'] == end_date
            assert summary['date_range']['total_days'] == 7
            
            assert summary['meal_statistics']['total_meals'] == 4
            assert summary['meal_statistics']['days_with_meals'] == 3
            assert summary['meal_statistics']['avg_meals_per_day'] == pytest.approx(0.6, rel=1e-1)
            
            assert summary['completion_statistics']['completed_meals'] == 2
            assert summary['completion_statistics']['completion_rate'] == 50.0
            
            assert summary['recipe_statistics']['unique_recipes'] == 3
            assert len(summary['recipe_statistics']['most_frequent_recipes']) <= 5
    
    def test_find_free_meal_slots(self):
        """Test finding free meal slots."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 2)
        
        # Mock existing plans (only breakfast on Jan 1)
        mock_plans = [
            Plan(
                id=1,
                date=date(2024, 1, 1),
                meal_type=MealType.BREAKFAST,
                recipe_id=1
            )
        ]
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = mock_plans
            
            free_slots = CalendarManager.find_free_meal_slots(start_date, end_date)
            
            # Should have 7 free slots (4 meal types * 2 days - 1 occupied)
            assert len(free_slots) == 7
            
            # Check that breakfast on Jan 1 is not in free slots
            breakfast_jan_1 = [
                slot for slot in free_slots 
                if slot['date'] == date(2024, 1, 1) and slot['meal_type'] == 'breakfast'
            ]
            assert len(breakfast_jan_1) == 0
            
            # Check that lunch on Jan 1 is in free slots
            lunch_jan_1 = [
                slot for slot in free_slots 
                if slot['date'] == date(2024, 1, 1) and slot['meal_type'] == 'lunch'
            ]
            assert len(lunch_jan_1) == 1
    
    def test_find_free_meal_slots_filtered(self):
        """Test finding free meal slots with meal type filter."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 1)
        
        # Mock no existing plans
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = []
            
            # Only check for breakfast and lunch
            free_slots = CalendarManager.find_free_meal_slots(
                start_date, 
                end_date, 
                meal_types=[MealType.BREAKFAST, MealType.LUNCH]
            )
            
            # Should have 2 free slots (breakfast and lunch for 1 day)
            assert len(free_slots) == 2
            
            meal_types = [slot['meal_type'] for slot in free_slots]
            assert 'breakfast' in meal_types
            assert 'lunch' in meal_types
            assert 'dinner' not in meal_types
            assert 'snack' not in meal_types
    
    def test_get_weekly_calendar_today_detection(self):
        """Test that today is correctly detected in weekly calendar."""
        today = date.today()
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = []
            
            calendar_data = CalendarManager.get_weekly_calendar(today)
            
            # Find today in the calendar
            today_data = None
            for day in calendar_data['days']:
                if day['date'] == today:
                    today_data = day
                    break
            
            assert today_data is not None
            assert today_data['is_today'] is True
    
    def test_get_weekly_calendar_weekend_detection(self):
        """Test that weekends are correctly detected in weekly calendar."""
        # Use a known Monday
        monday = date(2024, 1, 1)  # 2024-01-01 is a Monday
        
        with patch('mealplanner.calendar_management.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = []
            
            calendar_data = CalendarManager.get_weekly_calendar(monday)
            
            # Check weekend detection
            for i, day in enumerate(calendar_data['days']):
                if i < 5:  # Monday to Friday
                    assert day['is_weekend'] is False
                else:  # Saturday and Sunday
                    assert day['is_weekend'] is True
