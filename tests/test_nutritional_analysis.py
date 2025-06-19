"""
Tests for the nutritional analysis module.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from mealplanner.nutritional_analysis import NutritionData, NutritionalAnalyzer
from mealplanner.models import Recipe, Plan, Ingredient, MealType


class TestNutritionData:
    """Test the NutritionData class."""
    
    def test_nutrition_data_creation(self):
        """Test creating NutritionData object."""
        nutrition = NutritionData(
            calories=500.0,
            protein=25.0,
            carbs=60.0,
            fat=15.0,
            fiber=10.0,
            sugar=5.0,
            sodium=800.0
        )
        
        assert nutrition.calories == 500.0
        assert nutrition.protein == 25.0
        assert nutrition.carbs == 60.0
        assert nutrition.fat == 15.0
        assert nutrition.fiber == 10.0
        assert nutrition.sugar == 5.0
        assert nutrition.sodium == 800.0
    
    def test_nutrition_data_addition(self):
        """Test adding two NutritionData objects."""
        nutrition1 = NutritionData(calories=300, protein=15, carbs=30, fat=10)
        nutrition2 = NutritionData(calories=200, protein=10, carbs=20, fat=5)
        
        result = nutrition1 + nutrition2
        
        assert result.calories == 500
        assert result.protein == 25
        assert result.carbs == 50
        assert result.fat == 15
    
    def test_nutrition_data_multiplication(self):
        """Test multiplying NutritionData by a factor."""
        nutrition = NutritionData(calories=100, protein=10, carbs=15, fat=5)
        
        result = nutrition * 2.5
        
        assert result.calories == 250
        assert result.protein == 25
        assert result.carbs == 37.5
        assert result.fat == 12.5
    
    def test_nutrition_data_to_dict(self):
        """Test converting NutritionData to dictionary."""
        nutrition = NutritionData(
            calories=123.456,
            protein=12.345,
            carbs=23.456,
            fat=7.891
        )
        
        result = nutrition.to_dict()
        
        assert result['calories'] == 123.5
        assert result['protein'] == 12.3
        assert result['carbs'] == 23.5
        assert result['fat'] == 7.9


class TestNutritionalAnalyzer:
    """Test the NutritionalAnalyzer class."""
    
    def test_analyze_recipe_with_nutrition_data(self):
        """Test analyzing recipe that has nutritional data."""
        mock_recipe = Recipe(
            id=1,
            title="Test Recipe",
            calories=400.0,
            protein=20.0,
            carbs=50.0,
            fat=12.0,
            fiber=8.0,
            sugar=5.0,
            sodium=600.0
        )
        
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_recipe
            
            nutrition = NutritionalAnalyzer.analyze_recipe(1, servings=1)
            
            assert nutrition is not None
            assert nutrition.calories == 400.0
            assert nutrition.protein == 20.0
            assert nutrition.carbs == 50.0
            assert nutrition.fat == 12.0
    
    def test_analyze_recipe_with_servings(self):
        """Test analyzing recipe with multiple servings."""
        mock_recipe = Recipe(
            id=1,
            title="Test Recipe",
            calories=200.0,
            protein=10.0,
            carbs=25.0,
            fat=6.0
        )
        
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_recipe
            
            nutrition = NutritionalAnalyzer.analyze_recipe(1, servings=3)
            
            assert nutrition is not None
            assert nutrition.calories == 600.0
            assert nutrition.protein == 30.0
            assert nutrition.carbs == 75.0
            assert nutrition.fat == 18.0
    
    def test_analyze_recipe_not_found(self):
        """Test analyzing non-existent recipe."""
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            nutrition = NutritionalAnalyzer.analyze_recipe(999)
            
            assert nutrition is None
    
    def test_analyze_meal_plan(self):
        """Test analyzing a meal plan."""
        mock_plan = Plan(
            id=1,
            recipe_id=1,
            servings=2
        )
        
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_plan
            
            with patch('mealplanner.nutritional_analysis.NutritionalAnalyzer.analyze_recipe') as mock_analyze:
                mock_nutrition = NutritionData(calories=400, protein=20)
                mock_analyze.return_value = mock_nutrition
                
                nutrition = NutritionalAnalyzer.analyze_meal_plan(1)
                
                assert nutrition is not None
                assert nutrition.calories == 400
                mock_analyze.assert_called_once_with(1, 2)
    
    def test_analyze_meal_plan_not_found(self):
        """Test analyzing non-existent meal plan."""
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            nutrition = NutritionalAnalyzer.analyze_meal_plan(999)
            
            assert nutrition is None
    
    def test_analyze_daily_nutrition(self):
        """Test analyzing daily nutrition."""
        target_date = date(2024, 1, 15)
        
        mock_plans = [
            Plan(id=1, meal_type=MealType.BREAKFAST, recipe_id=1, servings=1, completed=True),
            Plan(id=2, meal_type=MealType.LUNCH, recipe_id=2, servings=1, completed=False)
        ]
        
        with patch('mealplanner.nutritional_analysis.MealPlanner.get_plans_for_date') as mock_get_plans:
            mock_get_plans.return_value = mock_plans
            
            with patch('mealplanner.nutritional_analysis.NutritionalAnalyzer.analyze_meal_plan') as mock_analyze:
                mock_analyze.side_effect = [
                    NutritionData(calories=300, protein=15),
                    NutritionData(calories=500, protein=25)
                ]
                
                analysis = NutritionalAnalyzer.analyze_daily_nutrition(target_date)
                
                assert analysis['date'] == target_date
                assert analysis['total_nutrition']['calories'] == 800
                assert analysis['total_nutrition']['protein'] == 40
                assert analysis['meal_count'] == 2
                assert analysis['completed_meals'] == 1
                assert 'breakfast' in analysis['meal_nutrition']
                assert 'lunch' in analysis['meal_nutrition']
    
    def test_analyze_period_nutrition(self):
        """Test analyzing nutrition for a period."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 16)
        
        with patch('mealplanner.nutritional_analysis.NutritionalAnalyzer.analyze_daily_nutrition') as mock_daily:
            mock_daily.side_effect = [
                {
                    'date': start_date,
                    'total_nutrition': {'calories': 2000, 'protein': 100, 'carbs': 250, 'fat': 67},
                    'meal_nutrition': {'breakfast': {'calories': 400, 'protein': 20}},
                    'meal_count': 3,
                    'completed_meals': 2
                },
                {
                    'date': end_date,
                    'total_nutrition': {'calories': 1800, 'protein': 90, 'carbs': 225, 'fat': 60},
                    'meal_nutrition': {'lunch': {'calories': 500, 'protein': 25}},
                    'meal_count': 3,
                    'completed_meals': 3
                }
            ]
            
            analysis = NutritionalAnalyzer.analyze_period_nutrition(start_date, end_date)
            
            assert analysis['start_date'] == start_date
            assert analysis['end_date'] == end_date
            assert analysis['total_days'] == 2
            assert analysis['total_nutrition']['calories'] == 3800
            assert analysis['total_nutrition']['protein'] == 190
            assert analysis['average_daily_nutrition']['calories'] == 1900
            assert analysis['average_daily_nutrition']['protein'] == 95
            assert len(analysis['daily_analyses']) == 2
    
    def test_calculate_macro_ratios(self):
        """Test calculating macronutrient ratios."""
        nutrition = NutritionData(
            calories=2000,  # This will be ignored in favor of calculated calories
            protein=100,    # 400 calories (100g * 4 cal/g)
            carbs=200,      # 800 calories (200g * 4 cal/g)
            fat=89          # 800 calories (89g * 9 cal/g) - approximately
        )
        
        ratios = NutritionalAnalyzer.calculate_macro_ratios(nutrition)
        
        # Total calculated calories: 400 + 800 + 801 = 2001
        assert abs(ratios['protein'] - 20.0) < 0.1  # 400/2001 * 100 ≈ 20%
        assert abs(ratios['carbs'] - 40.0) < 0.1    # 800/2001 * 100 ≈ 40%
        assert abs(ratios['fat'] - 40.0) < 0.1      # 801/2001 * 100 ≈ 40%
    
    def test_calculate_macro_ratios_zero_calories(self):
        """Test calculating macro ratios with zero calories."""
        nutrition = NutritionData()  # All zeros
        
        ratios = NutritionalAnalyzer.calculate_macro_ratios(nutrition)
        
        assert ratios['protein'] == 0.0
        assert ratios['carbs'] == 0.0
        assert ratios['fat'] == 0.0
    
    def test_assess_nutritional_balance_good(self):
        """Test assessing nutritional balance with good ratios."""
        nutrition = NutritionData(
            protein=100,    # 400 calories (20%)
            carbs=250,      # 1000 calories (50%)
            fat=67,         # 600 calories (30%)
            fiber=30,       # Good fiber
            sodium=2000     # Good sodium
        )
        
        assessment = NutritionalAnalyzer.assess_nutritional_balance(nutrition)
        
        assert assessment['balance_score'] == 3  # All macros in range
        assert assessment['balance_percentage'] == 100.0
        assert len(assessment['recommendations']) == 0  # No recommendations needed
    
    def test_assess_nutritional_balance_poor(self):
        """Test assessing nutritional balance with poor ratios."""
        nutrition = NutritionData(
            protein=25,     # 100 calories (5% - too low)
            carbs=400,      # 1600 calories (80% - too high)
            fat=17,         # 150 calories (15% - too low)
            fiber=10,       # Low fiber
            sodium=3000     # High sodium
        )
        
        assessment = NutritionalAnalyzer.assess_nutritional_balance(nutrition)
        
        assert assessment['balance_score'] == 0  # No macros in range
        assert assessment['balance_percentage'] == 0.0
        assert len(assessment['recommendations']) > 0  # Should have recommendations
        
        # Check for specific recommendations
        recommendations_text = ' '.join(assessment['recommendations'])
        assert 'protein' in recommendations_text.lower()
        assert 'carbs' in recommendations_text.lower() or 'carbohydrates' in recommendations_text.lower()
        assert 'fat' in recommendations_text.lower()
        assert 'fiber' in recommendations_text.lower()
        assert 'sodium' in recommendations_text.lower()
    
    def test_calculate_from_ingredients(self):
        """Test calculating nutrition from ingredients."""
        mock_ingredient = Ingredient(
            id=1,
            name="Test Ingredient",
            calories_per_100g=100,
            protein_per_100g=10,
            carbs_per_100g=15,
            fat_per_100g=5
        )
        
        # Mock the query result for recipe ingredients
        mock_ingredient_data = [(mock_ingredient, 200.0, "grams")]  # 200g of ingredient
        
        with patch('mealplanner.nutritional_analysis.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.join.return_value.filter.return_value.all.return_value = mock_ingredient_data
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            nutrition = NutritionalAnalyzer._calculate_from_ingredients(mock_session_obj, 1, 2)
            
            # 200g of ingredient with 100 cal/100g = 200 calories total
            # Divided by 2 servings = 100 calories per serving
            assert nutrition is not None
            assert nutrition.calories == 100.0
            assert nutrition.protein == 10.0
            assert nutrition.carbs == 15.0
            assert nutrition.fat == 5.0
