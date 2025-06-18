"""
Tests for the meal planning module.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from mealplanner.models import Base, Recipe, Plan, MealType
from mealplanner.meal_planning import MealPlanner, MealPlanningError


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_recipes(session):
    """Create sample recipes for testing."""
    recipes = [
        Recipe(
            id=1,
            title="Chicken Stir Fry",
            description="Quick and healthy chicken stir fry",
            prep_time=15,
            cook_time=10,
            servings=4,
            cuisine="Asian"
        ),
        Recipe(
            id=2,
            title="Pasta Carbonara",
            description="Classic Italian pasta dish",
            prep_time=10,
            cook_time=15,
            servings=2,
            cuisine="Italian"
        ),
        Recipe(
            id=3,
            title="Greek Salad",
            description="Fresh Mediterranean salad",
            prep_time=10,
            cook_time=0,
            servings=2,
            cuisine="Greek"
        )
    ]
    
    for recipe in recipes:
        session.add(recipe)
    session.commit()
    
    return recipes


@pytest.fixture
def sample_plans(session, sample_recipes):
    """Create sample meal plans for testing."""
    today = date.today()
    plans = [
        Plan(
            id=1,
            date=today,
            meal_type=MealType.BREAKFAST,
            recipe_id=1,
            servings=2,
            notes="Morning meal",
            completed=False
        ),
        Plan(
            id=2,
            date=today,
            meal_type=MealType.LUNCH,
            recipe_id=2,
            servings=1,
            completed=True
        ),
        Plan(
            id=3,
            date=today + timedelta(days=1),
            meal_type=MealType.DINNER,
            recipe_id=3,
            servings=2,
            completed=False
        )
    ]
    
    for plan in plans:
        session.add(plan)
    session.commit()
    
    return plans


class TestMealPlanner:
    """Test the MealPlanner class."""
    
    def test_schedule_meal_success(self, sample_recipes):
        """Test successful meal scheduling."""
        target_date = date.today() + timedelta(days=7)
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.side_effect = [
                sample_recipes[0],  # Recipe exists
                None  # No existing plan
            ]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            with patch('mealplanner.meal_planning.create_plan') as mock_create:
                mock_plan = Plan(
                    id=1,
                    date=target_date,
                    meal_type=MealType.DINNER,
                    recipe_id=1,
                    servings=2
                )
                mock_create.return_value = mock_plan
                
                plan = MealPlanner.schedule_meal(
                    target_date=target_date,
                    meal_type=MealType.DINNER,
                    recipe_id=1,
                    servings=2,
                    notes="Test meal"
                )
                
                assert plan.date == target_date
                assert plan.meal_type == MealType.DINNER
                assert plan.recipe_id == 1
                assert plan.servings == 2
    
    def test_schedule_meal_recipe_not_found(self):
        """Test scheduling meal with non-existent recipe."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            with pytest.raises(MealPlanningError, match="Recipe with ID 999 not found"):
                MealPlanner.schedule_meal(
                    target_date=date.today(),
                    meal_type=MealType.DINNER,
                    recipe_id=999
                )
    
    def test_schedule_meal_conflict_not_allowed(self, sample_recipes, sample_plans):
        """Test scheduling meal with conflict when not allowed."""
        target_date = date.today()
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.side_effect = [
                sample_recipes[0],  # Recipe exists
                sample_plans[0]  # Existing plan conflict
            ]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            with pytest.raises(MealPlanningError, match="already scheduled"):
                MealPlanner.schedule_meal(
                    target_date=target_date,
                    meal_type=MealType.BREAKFAST,
                    recipe_id=1,
                    allow_conflicts=False
                )
    
    def test_schedule_meal_conflict_allowed(self, sample_recipes, sample_plans):
        """Test scheduling meal with conflict when allowed."""
        target_date = date.today()
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.side_effect = [
                sample_recipes[0],  # Recipe exists
                sample_plans[0]  # Existing plan conflict (ignored)
            ]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            with patch('mealplanner.meal_planning.create_plan') as mock_create:
                mock_plan = Plan(
                    id=2,
                    date=target_date,
                    meal_type=MealType.BREAKFAST,
                    recipe_id=1,
                    servings=1
                )
                mock_create.return_value = mock_plan
                
                plan = MealPlanner.schedule_meal(
                    target_date=target_date,
                    meal_type=MealType.BREAKFAST,
                    recipe_id=1,
                    allow_conflicts=True
                )
                
                assert plan.id == 2
    
    def test_get_meal_plan_exists(self, sample_plans):
        """Test getting an existing meal plan."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = sample_plans[0]
            
            plan = MealPlanner.get_meal_plan(1)
            assert plan is not None
            assert plan.id == 1
    
    def test_get_meal_plan_not_exists(self):
        """Test getting a non-existent meal plan."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            plan = MealPlanner.get_meal_plan(999)
            assert plan is None
    
    def test_update_meal_plan_success(self, sample_plans):
        """Test successful meal plan update."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = sample_plans[0]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            updates = {"servings": 3, "notes": "Updated notes"}
            plan = MealPlanner.update_meal_plan(1, updates)
            
            assert plan is not None
            mock_session_obj.commit.assert_called_once()
    
    def test_update_meal_plan_not_found(self):
        """Test updating non-existent meal plan."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            plan = MealPlanner.update_meal_plan(999, {"servings": 3})
            assert plan is None
    
    def test_delete_meal_plan_success(self, sample_plans):
        """Test successful meal plan deletion."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.first.return_value = sample_plans[0]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            success = MealPlanner.delete_meal_plan(1)
            assert success is True
            mock_session_obj.delete.assert_called_once()
            mock_session_obj.commit.assert_called_once()
    
    def test_delete_meal_plan_not_found(self):
        """Test deleting non-existent meal plan."""
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            success = MealPlanner.delete_meal_plan(999)
            assert success is False
    
    def test_complete_meal(self, sample_plans):
        """Test marking meal as completed."""
        with patch('mealplanner.meal_planning.MealPlanner.update_meal_plan') as mock_update:
            mock_update.return_value = sample_plans[0]
            
            plan = MealPlanner.complete_meal(1, completed=True)
            assert plan is not None
            mock_update.assert_called_once_with(1, {'completed': True})
    
    def test_get_plans_for_date(self, sample_plans):
        """Test getting plans for a specific date."""
        target_date = date.today()
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
                sample_plans[0], sample_plans[1]
            ]
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            plans = MealPlanner.get_plans_for_date(target_date)
            assert len(plans) == 2
    
    def test_get_plans_for_date_range(self, sample_plans):
        """Test getting plans for a date range."""
        start_date = date.today()
        end_date = start_date + timedelta(days=7)
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.order_by.return_value.all.return_value = sample_plans
            mock_session_obj.expunge = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            plans = MealPlanner.get_plans_for_date_range(start_date, end_date)
            assert len(plans) == 3
    
    def test_clear_schedule(self, sample_plans):
        """Test clearing meal schedule."""
        start_date = date.today()
        end_date = start_date + timedelta(days=1)
        
        with patch('mealplanner.meal_planning.get_db_session') as mock_session:
            mock_session_obj = MagicMock()
            mock_session_obj.query.return_value.filter.return_value.all.return_value = sample_plans[:2]
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            count = MealPlanner.clear_schedule(start_date, end_date)
            assert count == 2
            assert mock_session_obj.delete.call_count == 2
            mock_session_obj.commit.assert_called_once()
    
    def test_plan_week(self, sample_recipes):
        """Test weekly meal planning."""
        start_date = date.today()
        recipe_assignments = {
            "monday_dinner": 1,
            "tuesday_lunch": 2,
            "wednesday_breakfast": 3
        }
        
        with patch('mealplanner.meal_planning.MealPlanner.schedule_meal') as mock_schedule:
            mock_plans = [
                Plan(id=1, date=start_date, meal_type=MealType.DINNER, recipe_id=1),
                Plan(id=2, date=start_date + timedelta(days=1), meal_type=MealType.LUNCH, recipe_id=2),
                Plan(id=3, date=start_date + timedelta(days=2), meal_type=MealType.BREAKFAST, recipe_id=3)
            ]
            mock_schedule.side_effect = mock_plans
            
            plans = MealPlanner.plan_week(start_date, recipe_assignments)
            assert len(plans) == 3
            assert mock_schedule.call_count == 3
    
    def test_get_meal_plan_statistics(self, sample_plans):
        """Test getting meal plan statistics."""
        start_date = date.today()
        end_date = start_date + timedelta(days=7)
        
        with patch('mealplanner.meal_planning.MealPlanner.get_plans_for_date_range') as mock_get_plans:
            mock_get_plans.return_value = sample_plans
            
            stats = MealPlanner.get_meal_plan_statistics(start_date, end_date)
            
            assert stats['total_plans'] == 3
            assert stats['completed_plans'] == 1
            assert stats['completion_rate'] == pytest.approx(33.33, rel=1e-2)
            assert 'meal_type_counts' in stats
            assert 'most_planned_recipes' in stats
