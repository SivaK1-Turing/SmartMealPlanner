"""
Tests for email template functionality.

Tests HTML and text template rendering for different email types.
"""

import pytest
from unittest.mock import Mock
from datetime import date, datetime

from mealplanner.email_templates import EmailTemplateManager
from mealplanner.models import Plan, Recipe, MealType


class TestEmailTemplateManager:
    """Test cases for EmailTemplateManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.template_manager = EmailTemplateManager()
        
        # Create mock meal plans
        self.mock_recipe1 = Mock()
        self.mock_recipe1.name = "Grilled Chicken"
        
        self.mock_recipe2 = Mock()
        self.mock_recipe2.name = "Caesar Salad"
        
        self.mock_plan1 = Mock()
        self.mock_plan1.meal_type = MealType.BREAKFAST
        self.mock_plan1.recipe = self.mock_recipe1
        self.mock_plan1.servings = 2
        self.mock_plan1.notes = "Extra spicy"
        self.mock_plan1.date = date(2024, 1, 15)
        
        self.mock_plan2 = Mock()
        self.mock_plan2.meal_type = MealType.LUNCH
        self.mock_plan2.recipe = self.mock_recipe2
        self.mock_plan2.servings = 1
        self.mock_plan2.notes = ""
        self.mock_plan2.date = date(2024, 1, 15)
    
    def test_template_manager_initialization(self):
        """Test EmailTemplateManager initialization."""
        manager = EmailTemplateManager()
        
        assert manager.base_styles is not None
        assert "font-family" in manager.base_styles
        assert "color" in manager.base_styles
    
    def test_render_meal_reminder_with_plans(self):
        """Test rendering meal reminder with meal plans."""
        target_date = date(2024, 1, 15)
        meal_plans = [self.mock_plan1, self.mock_plan2]
        
        html_content, text_content = self.template_manager.render_meal_reminder(
            target_date=target_date,
            meal_plans=meal_plans
        )
        
        # Check HTML content
        assert "Meal Reminder" in html_content
        assert "Monday, January 15, 2024" in html_content
        assert "Grilled Chicken" in html_content
        assert "Caesar Salad" in html_content
        assert "Breakfast" in html_content
        assert "Lunch" in html_content
        assert "Extra spicy" in html_content
        
        # Check text content
        assert "MEAL REMINDER" in text_content
        assert "Monday, January 15, 2024" in text_content
        assert "Grilled Chicken" in text_content
        assert "Caesar Salad" in text_content
        assert "Breakfast" in text_content
        assert "Lunch" in text_content
        assert "Extra spicy" in text_content
    
    def test_render_meal_reminder_no_plans(self):
        """Test rendering meal reminder with no meal plans."""
        target_date = date(2024, 1, 15)
        meal_plans = []
        
        html_content, text_content = self.template_manager.render_meal_reminder(
            target_date=target_date,
            meal_plans=meal_plans
        )
        
        # Check HTML content
        assert "Meal Reminder" in html_content
        assert "No meals scheduled" in html_content
        
        # Check text content
        assert "MEAL REMINDER" in text_content
        assert "No meals scheduled" in text_content
    
    def test_render_shopping_list(self):
        """Test rendering shopping list email."""
        # Create mock shopping list
        mock_shopping_list = Mock()
        mock_shopping_list.start_date = date(2024, 1, 15)
        mock_shopping_list.end_date = date(2024, 1, 16)
        mock_shopping_list.total_meals = 5
        mock_shopping_list.total_recipes = 3
        
        # Create mock shopping items
        mock_item1 = Mock()
        mock_item1.ingredient_name = "Chicken Breast"
        mock_item1.total_quantity = 500.0
        mock_item1.unit = "grams"
        mock_item1.category = "Meat"
        mock_item1.recipes_used = ["Grilled Chicken", "Chicken Salad"]
        
        mock_item2 = Mock()
        mock_item2.ingredient_name = "Lettuce"
        mock_item2.total_quantity = 200.0
        mock_item2.unit = "grams"
        mock_item2.category = "Vegetables"
        mock_item2.recipes_used = ["Caesar Salad"]
        
        mock_shopping_list.items = [mock_item1, mock_item2]
        
        html_content, text_content = self.template_manager.render_shopping_list(
            shopping_list=mock_shopping_list
        )
        
        # Check HTML content
        assert "Shopping List" in html_content
        assert "January 15 - 16, 2024" in html_content
        assert "2 Items" in html_content
        assert "5 Meals" in html_content
        assert "3 Recipes" in html_content
        assert "Chicken Breast" in html_content
        assert "500 grams" in html_content
        assert "Meat" in html_content
        assert "Grilled Chicken" in html_content
        
        # Check text content
        assert "SHOPPING LIST" in text_content
        assert "January 15 - 16, 2024" in text_content
        assert "Items: 2" in text_content
        assert "Meals: 5" in text_content
        assert "Recipes: 3" in text_content
        assert "Chicken Breast" in text_content
        assert "500 grams" in text_content
    
    def test_render_shopping_list_empty(self):
        """Test rendering empty shopping list."""
        mock_shopping_list = Mock()
        mock_shopping_list.start_date = date(2024, 1, 15)
        mock_shopping_list.end_date = date(2024, 1, 15)
        mock_shopping_list.total_meals = 0
        mock_shopping_list.total_recipes = 0
        mock_shopping_list.items = []
        
        html_content, text_content = self.template_manager.render_shopping_list(
            shopping_list=mock_shopping_list
        )
        
        # Check HTML content
        assert "Shopping List" in html_content
        assert "0 Items" in html_content
        assert "No shopping items found" in html_content
        
        # Check text content
        assert "SHOPPING LIST" in text_content
        assert "Items: 0" in text_content
        assert "No shopping items found" in text_content
    
    def test_render_nutrition_summary(self):
        """Test rendering nutrition summary email."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 21)
        period = "week"
        
        nutrition_data = {
            'total': {
                'calories': 2500,
                'protein': 150.5,
                'carbs': 300.2,
                'fat': 85.7,
                'fiber': 25.3,
                'sodium': 2300
            },
            'average': {
                'avg_calories': 357.1,
                'avg_protein': 21.5,
                'avg_carbs': 42.9,
                'avg_fat': 12.2,
                'avg_fiber': 3.6,
                'avg_sodium': 328.6
            },
            'meal_count': 7,
            'recipe_count': 5
        }
        
        meal_plans = [self.mock_plan1, self.mock_plan2]
        
        html_content, text_content = self.template_manager.render_nutrition_summary(
            start_date=start_date,
            end_date=end_date,
            period=period,
            nutrition_data=nutrition_data,
            meal_plans=meal_plans
        )
        
        # Check HTML content
        assert "Nutrition Summary" in html_content
        assert "Week" in html_content
        assert "January 15 - 21, 2024" in html_content
        assert "2500" in html_content  # calories
        assert "150.5" in html_content  # protein
        assert "7 Meals" in html_content
        assert "5 Recipes" in html_content
        
        # Check text content
        assert "NUTRITION SUMMARY" in text_content
        assert "Week" in text_content
        assert "January 15 - 21, 2024" in text_content
        assert "Calories: 2500" in text_content
        assert "Protein: 150.5" in text_content
        assert "Total Meals: 7" in text_content
        assert "Total Recipes: 5" in text_content
    
    def test_render_nutrition_summary_empty(self):
        """Test rendering nutrition summary with no data."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        period = "day"
        
        nutrition_data = {
            'total': {},
            'average': {},
            'meal_count': 0,
            'recipe_count': 0
        }
        
        meal_plans = []
        
        html_content, text_content = self.template_manager.render_nutrition_summary(
            start_date=start_date,
            end_date=end_date,
            period=period,
            nutrition_data=nutrition_data,
            meal_plans=meal_plans
        )
        
        # Check HTML content
        assert "Nutrition Summary" in html_content
        assert "Day" in html_content
        assert "No nutrition data available" in html_content
        assert "0 Meals" in html_content
        
        # Check text content
        assert "NUTRITION SUMMARY" in text_content
        assert "Day" in text_content
        assert "No nutrition data available" in text_content
        assert "Total Meals: 0" in text_content
    
    def test_render_weekly_meal_plan(self):
        """Test rendering weekly meal plan email."""
        start_date = date(2024, 1, 15)  # Monday
        end_date = date(2024, 1, 21)    # Sunday
        
        # Create meal plans for different days
        meal_plans = [self.mock_plan1, self.mock_plan2]
        
        # Create mock shopping list
        mock_shopping_list = Mock()
        mock_item = Mock()
        mock_item.total_quantity = 500.0
        mock_item.ingredient_name = "Test Item"
        mock_item.unit = "grams"
        mock_item.category = "Test Category"
        mock_item.recipes_used = ["Test Recipe"]
        mock_shopping_list.items = [mock_item]
        
        html_content, text_content = self.template_manager.render_weekly_meal_plan(
            start_date=start_date,
            end_date=end_date,
            meal_plans=meal_plans,
            shopping_list=mock_shopping_list
        )
        
        # Check HTML content
        assert "Weekly Meal Plan" in html_content
        assert "Week of January 15, 2024" in html_content
        assert "This Week's Meals" in html_content
        assert "Shopping List" in html_content
        assert "Monday" in html_content
        assert "Tuesday" in html_content
        assert "Sunday" in html_content
        
        # Check text content
        assert "WEEKLY MEAL PLAN" in text_content
        assert "Week of January 15, 2024" in text_content
        assert "This Week's Meals" in text_content
        assert "Shopping List" in text_content
        assert "Monday" in text_content
        assert "Tuesday" in text_content
        assert "Sunday" in text_content
    
    def test_render_weekly_meal_plan_no_shopping_list(self):
        """Test rendering weekly meal plan without shopping list."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 21)
        meal_plans = [self.mock_plan1]
        
        html_content, text_content = self.template_manager.render_weekly_meal_plan(
            start_date=start_date,
            end_date=end_date,
            meal_plans=meal_plans,
            shopping_list=None
        )
        
        # Check that shopping list section is not included
        assert "Weekly Meal Plan" in html_content
        assert "Shopping List" not in html_content
        
        assert "WEEKLY MEAL PLAN" in text_content
        assert "Shopping List" not in text_content
    
    def test_format_date_range_same_day(self):
        """Test date range formatting for same day."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        result = self.template_manager._format_date_range(start_date, end_date)
        
        assert result == "Monday, January 15, 2024"
    
    def test_format_date_range_same_month(self):
        """Test date range formatting for same month."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 20)
        
        result = self.template_manager._format_date_range(start_date, end_date)
        
        assert result == "January 15 - 20, 2024"
    
    def test_format_date_range_different_months(self):
        """Test date range formatting for different months."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 2, 5)
        
        result = self.template_manager._format_date_range(start_date, end_date)
        
        assert result == "January 15 - February 05, 2024"
    
    def test_format_date_range_different_years(self):
        """Test date range formatting for different years."""
        start_date = date(2023, 12, 25)
        end_date = date(2024, 1, 5)
        
        result = self.template_manager._format_date_range(start_date, end_date)
        
        assert result == "December 25, 2023 - January 05, 2024"
