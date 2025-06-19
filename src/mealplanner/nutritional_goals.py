"""
Nutritional goals functionality for the Smart Meal Planner application.

Handles goal setting, tracking, and progress analysis.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .nutritional_analysis import NutritionData, NutritionalAnalyzer

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Types of nutritional goals."""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    CUSTOM = "custom"


@dataclass
class NutritionalGoals:
    """Data class for nutritional goals."""
    goal_type: GoalType
    daily_calories: Optional[float] = None
    daily_protein: Optional[float] = None
    daily_carbs: Optional[float] = None
    daily_fat: Optional[float] = None
    daily_fiber: Optional[float] = None
    daily_sodium_max: Optional[float] = None
    
    # Macro ratios (as percentages)
    protein_ratio: Optional[float] = None
    carbs_ratio: Optional[float] = None
    fat_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'goal_type': self.goal_type.value,
            'daily_calories': self.daily_calories,
            'daily_protein': self.daily_protein,
            'daily_carbs': self.daily_carbs,
            'daily_fat': self.daily_fat,
            'daily_fiber': self.daily_fiber,
            'daily_sodium_max': self.daily_sodium_max,
            'protein_ratio': self.protein_ratio,
            'carbs_ratio': self.carbs_ratio,
            'fat_ratio': self.fat_ratio
        }


class NutritionalGoalManager:
    """Manages nutritional goals and progress tracking."""
    
    # Predefined goal templates
    GOAL_TEMPLATES = {
        GoalType.WEIGHT_LOSS: {
            'protein_ratio': 30,
            'carbs_ratio': 40,
            'fat_ratio': 30,
            'daily_fiber': 30,
            'daily_sodium_max': 2000
        },
        GoalType.WEIGHT_GAIN: {
            'protein_ratio': 25,
            'carbs_ratio': 50,
            'fat_ratio': 25,
            'daily_fiber': 25,
            'daily_sodium_max': 2300
        },
        GoalType.MAINTENANCE: {
            'protein_ratio': 20,
            'carbs_ratio': 50,
            'fat_ratio': 30,
            'daily_fiber': 25,
            'daily_sodium_max': 2300
        },
        GoalType.MUSCLE_GAIN: {
            'protein_ratio': 35,
            'carbs_ratio': 40,
            'fat_ratio': 25,
            'daily_fiber': 25,
            'daily_sodium_max': 2300
        },
        GoalType.ENDURANCE: {
            'protein_ratio': 15,
            'carbs_ratio': 60,
            'fat_ratio': 25,
            'daily_fiber': 30,
            'daily_sodium_max': 2300
        }
    }
    
    @staticmethod
    def create_goals_from_template(
        goal_type: GoalType,
        daily_calories: float,
        **overrides
    ) -> NutritionalGoals:
        """
        Create nutritional goals from a template.
        
        Args:
            goal_type: Type of goal
            daily_calories: Target daily calories
            **overrides: Override specific values
            
        Returns:
            NutritionalGoals object
        """
        template = NutritionalGoalManager.GOAL_TEMPLATES.get(goal_type, {})
        
        # Calculate macros from ratios and calories
        protein_ratio = overrides.get('protein_ratio', template.get('protein_ratio', 20))
        carbs_ratio = overrides.get('carbs_ratio', template.get('carbs_ratio', 50))
        fat_ratio = overrides.get('fat_ratio', template.get('fat_ratio', 30))
        
        # Calculate grams from calories and ratios
        daily_protein = (daily_calories * protein_ratio / 100) / 4  # 4 cal/g
        daily_carbs = (daily_calories * carbs_ratio / 100) / 4      # 4 cal/g
        daily_fat = (daily_calories * fat_ratio / 100) / 9          # 9 cal/g
        
        return NutritionalGoals(
            goal_type=goal_type,
            daily_calories=daily_calories,
            daily_protein=overrides.get('daily_protein', daily_protein),
            daily_carbs=overrides.get('daily_carbs', daily_carbs),
            daily_fat=overrides.get('daily_fat', daily_fat),
            daily_fiber=overrides.get('daily_fiber', template.get('daily_fiber', 25)),
            daily_sodium_max=overrides.get('daily_sodium_max', template.get('daily_sodium_max', 2300)),
            protein_ratio=protein_ratio,
            carbs_ratio=carbs_ratio,
            fat_ratio=fat_ratio
        )
    
    @staticmethod
    def calculate_progress(
        goals: NutritionalGoals,
        actual_nutrition: NutritionData
    ) -> Dict[str, Any]:
        """
        Calculate progress towards nutritional goals.
        
        Args:
            goals: Target nutritional goals
            actual_nutrition: Actual nutrition consumed
            
        Returns:
            Dictionary with progress analysis
        """
        progress = {}
        
        # Calculate progress for each nutrient
        nutrients = [
            ('calories', goals.daily_calories, actual_nutrition.calories),
            ('protein', goals.daily_protein, actual_nutrition.protein),
            ('carbs', goals.daily_carbs, actual_nutrition.carbs),
            ('fat', goals.daily_fat, actual_nutrition.fat),
            ('fiber', goals.daily_fiber, actual_nutrition.fiber)
        ]
        
        for nutrient, target, actual in nutrients:
            if target is not None:
                percentage = (actual / target * 100) if target > 0 else 0
                progress[nutrient] = {
                    'target': round(target, 1),
                    'actual': round(actual, 1),
                    'percentage': round(percentage, 1),
                    'remaining': round(max(0, target - actual), 1),
                    'status': NutritionalGoalManager._get_status(percentage, nutrient)
                }
        
        # Special handling for sodium (max limit)
        if goals.daily_sodium_max is not None:
            sodium_percentage = (actual_nutrition.sodium / goals.daily_sodium_max * 100) if goals.daily_sodium_max > 0 else 0
            progress['sodium'] = {
                'target_max': round(goals.daily_sodium_max, 1),
                'actual': round(actual_nutrition.sodium, 1),
                'percentage': round(sodium_percentage, 1),
                'over_limit': max(0, actual_nutrition.sodium - goals.daily_sodium_max),
                'status': 'good' if sodium_percentage <= 100 else 'over'
            }
        
        # Calculate overall progress score
        scores = []
        for nutrient, data in progress.items():
            if nutrient == 'sodium':
                # For sodium, good is <= 100%
                score = 100 if data['percentage'] <= 100 else max(0, 200 - data['percentage'])
            else:
                # For other nutrients, good is 80-120%
                percentage = data['percentage']
                if 80 <= percentage <= 120:
                    score = 100
                elif percentage < 80:
                    score = percentage * 1.25  # Scale up
                else:
                    score = max(0, 240 - percentage)  # Scale down
            scores.append(score)
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'progress': progress,
            'overall_score': round(overall_score, 1),
            'goal_type': goals.goal_type.value
        }
    
    @staticmethod
    def _get_status(percentage: float, nutrient: str) -> str:
        """Get status for a nutrient based on percentage of goal."""
        if nutrient == 'calories':
            if 90 <= percentage <= 110:
                return 'excellent'
            elif 80 <= percentage <= 120:
                return 'good'
            elif percentage < 80:
                return 'low'
            else:
                return 'high'
        else:
            if 80 <= percentage <= 120:
                return 'good'
            elif percentage < 80:
                return 'low'
            else:
                return 'high'
    
    @staticmethod
    def analyze_weekly_progress(
        goals: NutritionalGoals,
        start_date: date
    ) -> Dict[str, Any]:
        """
        Analyze weekly progress towards goals.
        
        Args:
            goals: Target nutritional goals
            start_date: Start of the week
            
        Returns:
            Dictionary with weekly progress analysis
        """
        end_date = start_date + timedelta(days=6)
        period_analysis = NutritionalAnalyzer.analyze_period_nutrition(start_date, end_date)
        
        daily_progresses = []
        weekly_totals = NutritionData(**period_analysis['total_nutrition'])
        weekly_averages = NutritionData(**period_analysis['average_daily_nutrition'])
        
        # Analyze each day
        for daily_analysis in period_analysis['daily_analyses']:
            daily_nutrition = NutritionData(**daily_analysis['total_nutrition'])
            daily_progress = NutritionalGoalManager.calculate_progress(goals, daily_nutrition)
            daily_progress['date'] = daily_analysis['date']
            daily_progresses.append(daily_progress)
        
        # Calculate weekly average progress
        weekly_progress = NutritionalGoalManager.calculate_progress(goals, weekly_averages)
        
        # Calculate consistency score (how consistent daily scores are)
        daily_scores = [dp['overall_score'] for dp in daily_progresses]
        if daily_scores:
            avg_score = sum(daily_scores) / len(daily_scores)
            score_variance = sum((score - avg_score) ** 2 for score in daily_scores) / len(daily_scores)
            consistency_score = max(0, 100 - score_variance)
        else:
            consistency_score = 0
        
        return {
            'week_start': start_date,
            'week_end': end_date,
            'daily_progresses': daily_progresses,
            'weekly_progress': weekly_progress,
            'weekly_totals': weekly_totals.to_dict(),
            'weekly_averages': weekly_averages.to_dict(),
            'consistency_score': round(consistency_score, 1),
            'days_with_data': len([dp for dp in daily_progresses if dp['overall_score'] > 0])
        }
    
    @staticmethod
    def generate_recommendations(
        goals: NutritionalGoals,
        actual_nutrition: NutritionData
    ) -> List[str]:
        """
        Generate nutritional recommendations based on goals and actual intake.
        
        Args:
            goals: Target nutritional goals
            actual_nutrition: Actual nutrition consumed
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        progress = NutritionalGoalManager.calculate_progress(goals, actual_nutrition)
        
        for nutrient, data in progress['progress'].items():
            if nutrient == 'sodium':
                if data['status'] == 'over':
                    recommendations.append(
                        f"Reduce sodium intake by {data['over_limit']:.0f}mg. "
                        f"Try using herbs and spices instead of salt."
                    )
            else:
                if data['status'] == 'low':
                    recommendations.append(
                        f"Increase {nutrient} intake by {data['remaining']:.0f}{'g' if nutrient != 'calories' else ' calories'}. "
                        f"Current: {data['actual']:.0f}, Target: {data['target']:.0f}"
                    )
                elif data['status'] == 'high':
                    over_amount = data['actual'] - data['target']
                    recommendations.append(
                        f"Consider reducing {nutrient} intake by {over_amount:.0f}{'g' if nutrient != 'calories' else ' calories'}. "
                        f"Current: {data['actual']:.0f}, Target: {data['target']:.0f}"
                    )
        
        # Add goal-specific recommendations
        if goals.goal_type == GoalType.WEIGHT_LOSS:
            if actual_nutrition.calories > (goals.daily_calories or 0):
                recommendations.append("Focus on portion control and choose lower-calorie, nutrient-dense foods.")
            if actual_nutrition.fiber < 25:
                recommendations.append("Increase fiber intake with vegetables, fruits, and whole grains to help with satiety.")
        
        elif goals.goal_type == GoalType.MUSCLE_GAIN:
            if actual_nutrition.protein < (goals.daily_protein or 0):
                recommendations.append("Include protein-rich foods like lean meats, eggs, dairy, or legumes in each meal.")
            if actual_nutrition.calories < (goals.daily_calories or 0):
                recommendations.append("Add healthy calorie-dense foods like nuts, avocados, and whole grains.")
        
        elif goals.goal_type == GoalType.ENDURANCE:
            if actual_nutrition.carbs < (goals.daily_carbs or 0):
                recommendations.append("Include complex carbohydrates like oats, quinoa, and sweet potatoes for sustained energy.")
        
        return recommendations[:5]  # Limit to top 5 recommendations
