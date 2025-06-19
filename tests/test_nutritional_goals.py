"""
Tests for the nutritional goals module.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from mealplanner.nutritional_goals import (
    GoalType, NutritionalGoals, NutritionalGoalManager
)
from mealplanner.nutritional_analysis import NutritionData


class TestNutritionalGoals:
    """Test the NutritionalGoals class."""
    
    def test_nutritional_goals_creation(self):
        """Test creating NutritionalGoals object."""
        goals = NutritionalGoals(
            goal_type=GoalType.WEIGHT_LOSS,
            daily_calories=1800,
            daily_protein=135,
            daily_carbs=180,
            daily_fat=60,
            daily_fiber=30,
            daily_sodium_max=2000,
            protein_ratio=30,
            carbs_ratio=40,
            fat_ratio=30
        )
        
        assert goals.goal_type == GoalType.WEIGHT_LOSS
        assert goals.daily_calories == 1800
        assert goals.daily_protein == 135
        assert goals.protein_ratio == 30
    
    def test_nutritional_goals_to_dict(self):
        """Test converting NutritionalGoals to dictionary."""
        goals = NutritionalGoals(
            goal_type=GoalType.MUSCLE_GAIN,
            daily_calories=2500,
            daily_protein=200
        )
        
        result = goals.to_dict()
        
        assert result['goal_type'] == 'muscle_gain'
        assert result['daily_calories'] == 2500
        assert result['daily_protein'] == 200


class TestNutritionalGoalManager:
    """Test the NutritionalGoalManager class."""
    
    def test_create_goals_from_template_weight_loss(self):
        """Test creating weight loss goals from template."""
        goals = NutritionalGoalManager.create_goals_from_template(
            goal_type=GoalType.WEIGHT_LOSS,
            daily_calories=1800
        )
        
        assert goals.goal_type == GoalType.WEIGHT_LOSS
        assert goals.daily_calories == 1800
        assert goals.protein_ratio == 30
        assert goals.carbs_ratio == 40
        assert goals.fat_ratio == 30
        assert goals.daily_fiber == 30
        assert goals.daily_sodium_max == 2000
        
        # Check calculated macros
        # Protein: 1800 * 30% / 4 cal/g = 135g
        assert abs(goals.daily_protein - 135) < 0.1
        # Carbs: 1800 * 40% / 4 cal/g = 180g
        assert abs(goals.daily_carbs - 180) < 0.1
        # Fat: 1800 * 30% / 9 cal/g = 60g
        assert abs(goals.daily_fat - 60) < 0.1
    
    def test_create_goals_from_template_muscle_gain(self):
        """Test creating muscle gain goals from template."""
        goals = NutritionalGoalManager.create_goals_from_template(
            goal_type=GoalType.MUSCLE_GAIN,
            daily_calories=2500
        )
        
        assert goals.goal_type == GoalType.MUSCLE_GAIN
        assert goals.daily_calories == 2500
        assert goals.protein_ratio == 35
        assert goals.carbs_ratio == 40
        assert goals.fat_ratio == 25
        
        # Check calculated macros
        # Protein: 2500 * 35% / 4 cal/g = 218.75g
        assert abs(goals.daily_protein - 218.75) < 0.1
    
    def test_create_goals_with_overrides(self):
        """Test creating goals with custom overrides."""
        goals = NutritionalGoalManager.create_goals_from_template(
            goal_type=GoalType.MAINTENANCE,
            daily_calories=2000,
            protein_ratio=25,
            daily_fiber=35,
            daily_sodium_max=1800
        )
        
        assert goals.protein_ratio == 25  # Override applied
        assert goals.daily_fiber == 35    # Override applied
        assert goals.daily_sodium_max == 1800  # Override applied
        assert goals.carbs_ratio == 50    # From template
    
    def test_calculate_progress_perfect_match(self):
        """Test calculating progress with perfect goal match."""
        goals = NutritionalGoals(
            goal_type=GoalType.MAINTENANCE,
            daily_calories=2000,
            daily_protein=100,
            daily_carbs=250,
            daily_fat=67,
            daily_fiber=25,
            daily_sodium_max=2300
        )
        
        actual_nutrition = NutritionData(
            calories=2000,
            protein=100,
            carbs=250,
            fat=67,
            fiber=25,
            sodium=2300
        )
        
        progress = NutritionalGoalManager.calculate_progress(goals, actual_nutrition)
        
        assert progress['goal_type'] == 'maintenance'
        assert progress['overall_score'] == 100.0
        
        # Check individual nutrients
        for nutrient in ['calories', 'protein', 'carbs', 'fat', 'fiber']:
            assert progress['progress'][nutrient]['percentage'] == 100.0
            assert progress['progress'][nutrient]['status'] == 'excellent' if nutrient == 'calories' else 'good'
        
        assert progress['progress']['sodium']['percentage'] == 100.0
        assert progress['progress']['sodium']['status'] == 'good'
    
    def test_calculate_progress_low_intake(self):
        """Test calculating progress with low nutrient intake."""
        goals = NutritionalGoals(
            goal_type=GoalType.WEIGHT_GAIN,
            daily_calories=2500,
            daily_protein=150,
            daily_carbs=300,
            daily_fat=80
        )
        
        actual_nutrition = NutritionData(
            calories=1500,  # 60% of goal
            protein=90,     # 60% of goal
            carbs=180,      # 60% of goal
            fat=48          # 60% of goal
        )
        
        progress = NutritionalGoalManager.calculate_progress(goals, actual_nutrition)
        
        # Check that all nutrients show as low
        for nutrient in ['calories', 'protein', 'carbs', 'fat']:
            assert progress['progress'][nutrient]['percentage'] == 60.0
            assert progress['progress'][nutrient]['status'] == 'low'
            assert progress['progress'][nutrient]['remaining'] > 0
    
    def test_calculate_progress_high_intake(self):
        """Test calculating progress with high nutrient intake."""
        goals = NutritionalGoals(
            goal_type=GoalType.WEIGHT_LOSS,
            daily_calories=1500,
            daily_protein=100,
            daily_sodium_max=2000
        )
        
        actual_nutrition = NutritionData(
            calories=2250,  # 150% of goal
            protein=150,    # 150% of goal
            sodium=3000     # 150% of limit
        )
        
        progress = NutritionalGoalManager.calculate_progress(goals, actual_nutrition)
        
        assert progress['progress']['calories']['percentage'] == 150.0
        assert progress['progress']['calories']['status'] == 'high'
        assert progress['progress']['protein']['percentage'] == 150.0
        assert progress['progress']['protein']['status'] == 'high'
        assert progress['progress']['sodium']['percentage'] == 150.0
        assert progress['progress']['sodium']['status'] == 'over'
        assert progress['progress']['sodium']['over_limit'] == 1000.0
    
    def test_get_status_calories(self):
        """Test status calculation for calories."""
        assert NutritionalGoalManager._get_status(95, 'calories') == 'excellent'
        assert NutritionalGoalManager._get_status(85, 'calories') == 'good'
        assert NutritionalGoalManager._get_status(75, 'calories') == 'low'
        assert NutritionalGoalManager._get_status(125, 'calories') == 'high'
    
    def test_get_status_other_nutrients(self):
        """Test status calculation for other nutrients."""
        assert NutritionalGoalManager._get_status(90, 'protein') == 'good'
        assert NutritionalGoalManager._get_status(75, 'protein') == 'low'
        assert NutritionalGoalManager._get_status(125, 'protein') == 'high'
    
    def test_analyze_weekly_progress(self):
        """Test analyzing weekly progress."""
        goals = NutritionalGoals(
            goal_type=GoalType.MAINTENANCE,
            daily_calories=2000,
            daily_protein=100
        )
        
        start_date = date(2024, 1, 15)
        
        # Mock period analysis
        mock_period_analysis = {
            'total_nutrition': {'calories': 14000, 'protein': 700, 'carbs': 1750, 'fat': 467},
            'average_daily_nutrition': {'calories': 2000, 'protein': 100, 'carbs': 250, 'fat': 67},
            'daily_analyses': [
                {
                    'date': start_date + timedelta(days=i),
                    'total_nutrition': {'calories': 2000, 'protein': 100, 'carbs': 250, 'fat': 67}
                }
                for i in range(7)
            ]
        }
        
        with patch('mealplanner.nutritional_goals.NutritionalAnalyzer.analyze_period_nutrition') as mock_analyze:
            mock_analyze.return_value = mock_period_analysis
            
            weekly_progress = NutritionalGoalManager.analyze_weekly_progress(goals, start_date)
            
            assert weekly_progress['week_start'] == start_date
            assert weekly_progress['week_end'] == start_date + timedelta(days=6)
            assert len(weekly_progress['daily_progresses']) == 7
            assert weekly_progress['days_with_data'] == 7
            assert weekly_progress['consistency_score'] == 100.0  # Perfect consistency
            
            # Check weekly progress
            assert weekly_progress['weekly_progress']['overall_score'] == 100.0
    
    def test_generate_recommendations_weight_loss(self):
        """Test generating recommendations for weight loss goals."""
        goals = NutritionalGoals(
            goal_type=GoalType.WEIGHT_LOSS,
            daily_calories=1500,
            daily_protein=100,
            daily_fiber=30
        )

        actual_nutrition = NutritionData(
            calories=1800,  # Too high
            protein=70,     # Too low (70% of goal, should be "low")
            fiber=15        # Too low
        )

        recommendations = NutritionalGoalManager.generate_recommendations(goals, actual_nutrition)

        assert len(recommendations) > 0
        recommendations_text = ' '.join(recommendations).lower()

        # Should have recommendations for high calories, low protein, low fiber
        assert any('calorie' in rec.lower() for rec in recommendations)
        assert any('protein' in rec.lower() for rec in recommendations)
        assert any('fiber' in rec.lower() for rec in recommendations)

        # Should have weight loss specific advice
        assert any('portion control' in rec.lower() or 'satiety' in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_muscle_gain(self):
        """Test generating recommendations for muscle gain goals."""
        goals = NutritionalGoals(
            goal_type=GoalType.MUSCLE_GAIN,
            daily_calories=2500,
            daily_protein=200
        )
        
        actual_nutrition = NutritionData(
            calories=2000,  # Too low
            protein=150     # Too low
        )
        
        recommendations = NutritionalGoalManager.generate_recommendations(goals, actual_nutrition)
        
        assert len(recommendations) > 0
        recommendations_text = ' '.join(recommendations).lower()
        
        # Should have muscle gain specific advice
        assert any('protein' in rec.lower() and ('meat' in rec.lower() or 'egg' in rec.lower()) for rec in recommendations)
        assert any('calorie' in rec.lower() and ('nuts' in rec.lower() or 'avocado' in rec.lower()) for rec in recommendations)
    
    def test_generate_recommendations_endurance(self):
        """Test generating recommendations for endurance goals."""
        goals = NutritionalGoals(
            goal_type=GoalType.ENDURANCE,
            daily_carbs=400
        )
        
        actual_nutrition = NutritionData(
            carbs=250  # Too low
        )
        
        recommendations = NutritionalGoalManager.generate_recommendations(goals, actual_nutrition)
        
        assert len(recommendations) > 0
        recommendations_text = ' '.join(recommendations).lower()
        
        # Should have endurance specific advice
        assert any('carb' in rec.lower() and ('oats' in rec.lower() or 'quinoa' in rec.lower()) for rec in recommendations)
    
    def test_generate_recommendations_limit_count(self):
        """Test that recommendations are limited to 5."""
        goals = NutritionalGoals(
            goal_type=GoalType.CUSTOM,
            daily_calories=2000,
            daily_protein=100,
            daily_carbs=250,
            daily_fat=67,
            daily_fiber=25,
            daily_sodium_max=2000
        )
        
        # Create nutrition that's off for all nutrients
        actual_nutrition = NutritionData(
            calories=1000,  # Too low
            protein=50,     # Too low
            carbs=125,      # Too low
            fat=33,         # Too low
            fiber=12,       # Too low
            sodium=3000     # Too high
        )
        
        recommendations = NutritionalGoalManager.generate_recommendations(goals, actual_nutrition)
        
        # Should be limited to 5 recommendations
        assert len(recommendations) <= 5
