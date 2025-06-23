"""
Email template management for the Smart Meal Planner application.

Provides HTML and text templates for various email notifications:
- Meal reminders
- Shopping list emails
- Nutrition summaries
- Weekly meal plan summaries
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from string import Template

logger = logging.getLogger(__name__)


class EmailTemplateManager:
    """Manages email templates for different notification types."""
    
    def __init__(self):
        """Initialize email template manager."""
        self.base_styles = self._get_base_styles()
    
    def _get_base_styles(self) -> str:
        """Get base CSS styles for HTML emails."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header {
                text-align: center;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            .header h1 {
                color: #4CAF50;
                margin: 0;
                font-size: 28px;
            }
            .header .subtitle {
                color: #666;
                font-size: 16px;
                margin-top: 5px;
            }
            .section {
                margin-bottom: 25px;
            }
            .section h2 {
                color: #2E7D32;
                border-left: 4px solid #4CAF50;
                padding-left: 15px;
                margin-bottom: 15px;
            }
            .meal-item {
                background-color: #f8f9fa;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 5px;
                border-left: 4px solid #4CAF50;
            }
            .meal-time {
                font-weight: bold;
                color: #2E7D32;
                font-size: 14px;
                text-transform: uppercase;
            }
            .meal-name {
                font-size: 18px;
                font-weight: bold;
                margin: 5px 0;
            }
            .meal-details {
                color: #666;
                font-size: 14px;
            }
            .shopping-item {
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }
            .shopping-category {
                font-weight: bold;
                color: #2E7D32;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 16px;
                text-transform: uppercase;
            }
            .nutrition-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .nutrition-card {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
                border: 1px solid #e9ecef;
            }
            .nutrition-value {
                font-size: 24px;
                font-weight: bold;
                color: #2E7D32;
            }
            .nutrition-label {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }
            .footer {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 14px;
            }
            .button {
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin: 10px 0;
            }
            .summary-stats {
                background-color: #e8f5e8;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }
            .stat-item {
                display: inline-block;
                margin-right: 20px;
                font-weight: bold;
            }
        </style>
        """
    
    def render_meal_reminder(
        self,
        target_date: date,
        meal_plans: List[Any]
    ) -> Tuple[str, str]:
        """
        Render meal reminder email templates.
        
        Args:
            target_date: Date for the meal reminder
            meal_plans: List of meal plans for the date
            
        Returns:
            Tuple of (html_content, text_content)
        """
        date_str = target_date.strftime('%A, %B %d, %Y')
        
        # HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Meal Reminder</title>
            {self.base_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🍽️ Meal Reminder</h1>
                    <div class="subtitle">{date_str}</div>
                </div>
                
                <div class="section">
                    <h2>Today's Meals</h2>
                    {self._render_meal_plans_html(meal_plans)}
                </div>
                
                <div class="footer">
                    <p>Happy cooking! 👨‍🍳</p>
                    <p><em>Smart Meal Planner - Making meal planning effortless</em></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text template
        text_content = f"""
        MEAL REMINDER - {date_str}
        ========================================
        
        Today's Meals:
        {self._render_meal_plans_text(meal_plans)}
        
        Happy cooking!
        
        --
        Smart Meal Planner
        Making meal planning effortless
        """
        
        return html_template, text_content
    
    def render_shopping_list(
        self,
        shopping_list: Any
    ) -> Tuple[str, str]:
        """
        Render shopping list email templates.
        
        Args:
            shopping_list: Shopping list object
            
        Returns:
            Tuple of (html_content, text_content)
        """
        date_range = self._format_date_range(shopping_list.start_date, shopping_list.end_date)
        
        # HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Shopping List</title>
            {self.base_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛒 Shopping List</h1>
                    <div class="subtitle">{date_range}</div>
                </div>
                
                <div class="summary-stats">
                    <span class="stat-item">📋 {len(shopping_list.items)} Items</span>
                    <span class="stat-item">🍽️ {shopping_list.total_meals} Meals</span>
                    <span class="stat-item">📖 {shopping_list.total_recipes} Recipes</span>
                </div>
                
                <div class="section">
                    <h2>Shopping Items</h2>
                    {self._render_shopping_items_html(shopping_list)}
                </div>
                
                <div class="footer">
                    <p>Happy shopping! 🛍️</p>
                    <p><em>Smart Meal Planner - Making meal planning effortless</em></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text template
        text_content = f"""
        SHOPPING LIST - {date_range}
        ========================================
        
        Summary:
        - Items: {len(shopping_list.items)}
        - Meals: {shopping_list.total_meals}
        - Recipes: {shopping_list.total_recipes}
        
        Shopping Items:
        {self._render_shopping_items_text(shopping_list)}
        
        Happy shopping!
        
        --
        Smart Meal Planner
        Making meal planning effortless
        """
        
        return html_template, text_content

    def render_weekly_meal_plan(
        self,
        start_date: date,
        end_date: date,
        meal_plans: List[Any],
        shopping_list: Optional[Any] = None
    ) -> Tuple[str, str]:
        """
        Render weekly meal plan email templates.

        Args:
            start_date: Start date of the week
            end_date: End date of the week
            meal_plans: List of meal plans for the week
            shopping_list: Optional shopping list for the week

        Returns:
            Tuple of (html_content, text_content)
        """
        week_str = f"Week of {start_date.strftime('%B %d, %Y')}"

        # HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Weekly Meal Plan</title>
            {self.base_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Weekly Meal Plan</h1>
                    <div class="subtitle">{week_str}</div>
                </div>

                <div class="section">
                    <h2>This Week's Meals</h2>
                    {self._render_weekly_meals_html(meal_plans, start_date, end_date)}
                </div>

                {self._render_shopping_section_html(shopping_list) if shopping_list and shopping_list.items else ''}

                <div class="footer">
                    <p>Have a delicious week! 🌟</p>
                    <p><em>Smart Meal Planner - Making meal planning effortless</em></p>
                </div>
            </div>
        </body>
        </html>
        """

        # Text template
        text_content = f"""
        WEEKLY MEAL PLAN
        {week_str}
        ========================================

        This Week's Meals:
        {self._render_weekly_meals_text(meal_plans, start_date, end_date)}

        {self._render_shopping_section_text(shopping_list) if shopping_list and shopping_list.items else ''}

        Have a delicious week!

        --
        Smart Meal Planner
        Making meal planning effortless
        """

        return html_template, text_content

    def _render_meal_plans_html(self, meal_plans: List[Any]) -> str:
        """Render meal plans as HTML."""
        if not meal_plans:
            return '<p>No meals scheduled for today.</p>'

        html_parts = []
        for plan in meal_plans:
            meal_time = getattr(plan, 'meal_type', 'Unknown').value.title()
            recipe_name = getattr(plan.recipe, 'name', 'Unknown Recipe') if hasattr(plan, 'recipe') and plan.recipe else 'Unknown Recipe'
            servings = getattr(plan, 'servings', 1)
            notes = getattr(plan, 'notes', '')

            html_parts.append(f"""
                <div class="meal-item">
                    <div class="meal-time">{meal_time}</div>
                    <div class="meal-name">{recipe_name}</div>
                    <div class="meal-details">Servings: {servings}</div>
                    {f'<div class="meal-details">Notes: {notes}</div>' if notes else ''}
                </div>
            """)

        return ''.join(html_parts)

    def _render_meal_plans_text(self, meal_plans: List[Any]) -> str:
        """Render meal plans as plain text."""
        if not meal_plans:
            return 'No meals scheduled for today.'

        text_parts = []
        for plan in meal_plans:
            meal_time = getattr(plan, 'meal_type', 'Unknown').value.title()
            recipe_name = getattr(plan.recipe, 'name', 'Unknown Recipe') if hasattr(plan, 'recipe') and plan.recipe else 'Unknown Recipe'
            servings = getattr(plan, 'servings', 1)
            notes = getattr(plan, 'notes', '')

            text_parts.append(f"• {meal_time}: {recipe_name} ({servings} servings)")
            if notes:
                text_parts.append(f"  Notes: {notes}")

        return '\n'.join(text_parts)

    def _render_shopping_items_html(self, shopping_list: Any) -> str:
        """Render shopping items as HTML grouped by category."""
        if not shopping_list.items:
            return '<p>No shopping items found.</p>'

        # Group items by category
        categories = {}
        for item in shopping_list.items:
            category = item.category or 'Other'
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        html_parts = []
        for category, items in sorted(categories.items()):
            html_parts.append(f'<div class="shopping-category">{category}</div>')
            for item in items:
                quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                recipes_str = ', '.join(item.recipes_used) if item.recipes_used else ''

                html_parts.append(f"""
                    <div class="shopping-item">
                        <strong>{item.ingredient_name}</strong> - {quantity_str} {item.unit}
                        {f'<br><small>Used in: {recipes_str}</small>' if recipes_str else ''}
                    </div>
                """)

        return ''.join(html_parts)

    def _render_shopping_items_text(self, shopping_list: Any) -> str:
        """Render shopping items as plain text grouped by category."""
        if not shopping_list.items:
            return 'No shopping items found.'

        # Group items by category
        categories = {}
        for item in shopping_list.items:
            category = item.category or 'Other'
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        text_parts = []
        for category, items in sorted(categories.items()):
            text_parts.append(f'\n{category.upper()}:')
            text_parts.append('-' * (len(category) + 1))
            for item in items:
                quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                recipes_str = ', '.join(item.recipes_used) if item.recipes_used else ''

                line = f"• {item.ingredient_name} - {quantity_str} {item.unit}"
                if recipes_str:
                    line += f" (used in: {recipes_str})"
                text_parts.append(line)

        return '\n'.join(text_parts)

    def _render_nutrition_data_html(self, nutrition_data: Dict[str, Any]) -> str:
        """Render nutrition data as HTML."""
        total = nutrition_data.get('total', {})

        if not total:
            return '<p>No nutrition data available.</p>'

        return f"""
            <div class="nutrition-grid">
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('calories', 0):.0f}</div>
                    <div class="nutrition-label">Calories</div>
                </div>
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('protein', 0):.1f}g</div>
                    <div class="nutrition-label">Protein</div>
                </div>
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('carbs', 0):.1f}g</div>
                    <div class="nutrition-label">Carbs</div>
                </div>
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('fat', 0):.1f}g</div>
                    <div class="nutrition-label">Fat</div>
                </div>
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('fiber', 0):.1f}g</div>
                    <div class="nutrition-label">Fiber</div>
                </div>
                <div class="nutrition-card">
                    <div class="nutrition-value">{total.get('sodium', 0):.0f}mg</div>
                    <div class="nutrition-label">Sodium</div>
                </div>
            </div>
        """

    def _render_nutrition_data_text(self, nutrition_data: Dict[str, Any]) -> str:
        """Render nutrition data as plain text."""
        total = nutrition_data.get('total', {})

        if not total:
            return 'No nutrition data available.'

        return f"""
        - Calories: {total.get('calories', 0):.0f}
        - Protein: {total.get('protein', 0):.1f}g
        - Carbohydrates: {total.get('carbs', 0):.1f}g
        - Fat: {total.get('fat', 0):.1f}g
        - Fiber: {total.get('fiber', 0):.1f}g
        - Sodium: {total.get('sodium', 0):.0f}mg
        """

    def _render_weekly_meals_html(self, meal_plans: List[Any], start_date: date, end_date: date) -> str:
        """Render weekly meals as HTML organized by day."""
        from datetime import timedelta

        # Group meals by date
        meals_by_date = {}
        for plan in meal_plans:
            plan_date = getattr(plan, 'date', None)
            if plan_date:
                if plan_date not in meals_by_date:
                    meals_by_date[plan_date] = []
                meals_by_date[plan_date].append(plan)

        html_parts = []
        current_date = start_date

        while current_date <= end_date:
            day_name = current_date.strftime('%A')
            date_str = current_date.strftime('%B %d')

            html_parts.append(f'<h3>{day_name}, {date_str}</h3>')

            if current_date in meals_by_date:
                html_parts.append(self._render_meal_plans_html(meals_by_date[current_date]))
            else:
                html_parts.append('<p style="color: #666; font-style: italic;">No meals scheduled</p>')

            current_date += timedelta(days=1)

        return ''.join(html_parts)

    def _render_weekly_meals_text(self, meal_plans: List[Any], start_date: date, end_date: date) -> str:
        """Render weekly meals as plain text organized by day."""
        from datetime import timedelta

        # Group meals by date
        meals_by_date = {}
        for plan in meal_plans:
            plan_date = getattr(plan, 'date', None)
            if plan_date:
                if plan_date not in meals_by_date:
                    meals_by_date[plan_date] = []
                meals_by_date[plan_date].append(plan)

        text_parts = []
        current_date = start_date

        while current_date <= end_date:
            day_name = current_date.strftime('%A')
            date_str = current_date.strftime('%B %d')

            text_parts.append(f'\n{day_name}, {date_str}:')
            text_parts.append('-' * (len(day_name) + len(date_str) + 2))

            if current_date in meals_by_date:
                text_parts.append(self._render_meal_plans_text(meals_by_date[current_date]))
            else:
                text_parts.append('No meals scheduled')

            current_date += timedelta(days=1)

        return '\n'.join(text_parts)

    def _render_shopping_section_html(self, shopping_list: Any) -> str:
        """Render shopping list section for weekly meal plan HTML."""
        return f"""
            <div class="section">
                <h2>Shopping List</h2>
                <div class="summary-stats">
                    <span class="stat-item">📋 {len(shopping_list.items)} Items</span>
                </div>
                {self._render_shopping_items_html(shopping_list)}
            </div>
        """

    def _render_shopping_section_text(self, shopping_list: Any) -> str:
        """Render shopping list section for weekly meal plan text."""
        return f"""
        Shopping List ({len(shopping_list.items)} items):
        ========================================
        {self._render_shopping_items_text(shopping_list)}
        """

    def _format_date_range(self, start_date: date, end_date: date) -> str:
        """Format a date range for display."""
        if start_date == end_date:
            return start_date.strftime('%A, %B %d, %Y')
        elif start_date.year == end_date.year and start_date.month == end_date.month:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%d, %Y')}"
        elif start_date.year == end_date.year:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        else:
            return f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    def render_nutrition_summary(
        self,
        start_date: date,
        end_date: date,
        period: str,
        nutrition_data: Dict[str, Any],
        meal_plans: List[Any]
    ) -> Tuple[str, str]:
        """
        Render nutrition summary email templates.
        
        Args:
            start_date: Start date of the period
            end_date: End date of the period
            period: Period type ('day', 'week', 'month')
            nutrition_data: Nutrition summary data
            meal_plans: List of meal plans
            
        Returns:
            Tuple of (html_content, text_content)
        """
        date_range = self._format_date_range(start_date, end_date)
        period_title = period.title()
        
        # HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nutrition Summary</title>
            {self.base_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Nutrition Summary</h1>
                    <div class="subtitle">{period_title} - {date_range}</div>
                </div>
                
                <div class="section">
                    <h2>Nutritional Overview</h2>
                    {self._render_nutrition_data_html(nutrition_data)}
                </div>
                
                <div class="section">
                    <h2>Meal Summary</h2>
                    <div class="summary-stats">
                        <span class="stat-item">🍽️ {nutrition_data.get('meal_count', 0)} Meals</span>
                        <span class="stat-item">📖 {nutrition_data.get('recipe_count', 0)} Recipes</span>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Keep up the great nutrition! 💪</p>
                    <p><em>Smart Meal Planner - Making meal planning effortless</em></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text template
        text_content = f"""
        NUTRITION SUMMARY - {period_title}
        {date_range}
        ========================================
        
        Nutritional Overview:
        {self._render_nutrition_data_text(nutrition_data)}
        
        Meal Summary:
        - Total Meals: {nutrition_data.get('meal_count', 0)}
        - Total Recipes: {nutrition_data.get('recipe_count', 0)}
        
        Keep up the great nutrition!
        
        --
        Smart Meal Planner
        Making meal planning effortless
        """
        
        return html_template, text_content
