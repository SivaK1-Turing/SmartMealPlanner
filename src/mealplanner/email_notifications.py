"""
Email notification functionality for the Smart Meal Planner application.

Provides SMTP configuration, email sending, and template rendering for:
- Meal reminders and notifications
- Shopping list emails
- Nutrition summary reports
- Weekly meal plan summaries
"""

import logging
import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import tempfile
import os

from .config import get_config
from .shopping_list import ShoppingListGenerator
from .shopping_list_export import ShoppingListExporter
from .nutritional_analysis import NutritionalAnalyzer
from .meal_planning import MealPlanner

logger = logging.getLogger(__name__)


class EmailConfigurationError(Exception):
    """Raised when email configuration is invalid or missing."""
    pass


class EmailSendError(Exception):
    """Raised when email sending fails."""
    pass


class EmailNotificationManager:
    """Manages email notifications for meal planning activities."""
    
    def __init__(self):
        """Initialize email notification manager."""
        self.config = get_config()
        self._smtp_config = None
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate email configuration."""
        required_settings = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD']
        missing_settings = []
        
        for setting in required_settings:
            if not self.config.get(setting):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.warning(f"Missing email configuration: {', '.join(missing_settings)}")
            # Don't raise error here - allow graceful degradation
    
    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration from environment variables."""
        if self._smtp_config is None:
            self._smtp_config = {
                'host': self.config.get('SMTP_HOST'),
                'port': int(self.config.get('SMTP_PORT', '587')),
                'username': self.config.get('SMTP_USERNAME'),
                'password': self.config.get('SMTP_PASSWORD'),
                'use_tls': self.config.get('SMTP_USE_TLS', 'true').lower() == 'true',
                'from_name': self.config.get('SMTP_FROM_NAME', 'Smart Meal Planner'),
                'from_email': self.config.get('SMTP_FROM_EMAIL') or self.config.get('SMTP_USERNAME')
            }
        return self._smtp_config
    
    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            smtp_config = self._get_smtp_config()
            
            if not all([smtp_config['host'], smtp_config['username'], smtp_config['password']]):
                logger.error("Missing required SMTP configuration")
                return False
            
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                logger.info("SMTP connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            attachments: List of attachment dictionaries with 'filename' and 'content' keys
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            
        Returns:
            True if email sent successfully, False otherwise
            
        Raises:
            EmailConfigurationError: If email configuration is invalid
            EmailSendError: If email sending fails
        """
        try:
            smtp_config = self._get_smtp_config()
            
            if not all([smtp_config['host'], smtp_config['username'], smtp_config['password']]):
                raise EmailConfigurationError("Missing required SMTP configuration")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
            msg['To'] = to_email
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise EmailSendError(f"Failed to send email: {e}")
    
    def send_meal_reminder(
        self,
        to_email: str,
        target_date: date,
        meal_plans: Optional[List[Any]] = None
    ) -> bool:
        """
        Send a meal reminder email for a specific date.
        
        Args:
            to_email: Recipient email address
            target_date: Date for meal reminder
            meal_plans: Optional list of meal plans (will fetch if not provided)
            
        Returns:
            True if email sent successfully
        """
        from .email_templates import EmailTemplateManager
        
        try:
            # Get meal plans if not provided
            if meal_plans is None:
                meal_plans = MealPlanner.get_plans_for_date_range(
                    start_date=target_date,
                    end_date=target_date
                )
            
            template_manager = EmailTemplateManager()
            html_content, text_content = template_manager.render_meal_reminder(
                target_date=target_date,
                meal_plans=meal_plans
            )
            
            subject = f"Meal Reminder for {target_date.strftime('%B %d, %Y')}"
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send meal reminder: {e}")
            return False
    
    def send_shopping_list(
        self,
        to_email: str,
        start_date: date,
        end_date: Optional[date] = None,
        format_type: str = "html",
        include_attachment: bool = True
    ) -> bool:
        """
        Send a shopping list email for a date range.
        
        Args:
            to_email: Recipient email address
            start_date: Start date for shopping list
            end_date: End date for shopping list (defaults to start_date)
            format_type: Format for email content ('html' or 'text')
            include_attachment: Whether to include shopping list as attachment
            
        Returns:
            True if email sent successfully
        """
        from .email_templates import EmailTemplateManager
        
        try:
            if end_date is None:
                end_date = start_date
            
            # Generate shopping list
            shopping_list = ShoppingListGenerator.generate_from_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            if not shopping_list.items:
                logger.warning(f"No shopping list items found for {start_date} to {end_date}")
                return False
            
            template_manager = EmailTemplateManager()
            html_content, text_content = template_manager.render_shopping_list(
                shopping_list=shopping_list
            )
            
            # Prepare attachments
            attachments = []
            if include_attachment:
                # Create text attachment
                text_export = ShoppingListExporter.export_to_text(shopping_list)
                attachments.append({
                    'filename': f'shopping_list_{start_date}_{end_date}.txt',
                    'content': text_export.encode('utf-8')
                })
                
                # Create CSV attachment
                csv_export = ShoppingListExporter.export_to_csv(shopping_list)
                attachments.append({
                    'filename': f'shopping_list_{start_date}_{end_date}.csv',
                    'content': csv_export.encode('utf-8')
                })
            
            date_range = f"{start_date.strftime('%B %d')}"
            if end_date != start_date:
                date_range += f" - {end_date.strftime('%B %d, %Y')}"
            else:
                date_range += f", {start_date.strftime('%Y')}"
            
            subject = f"Shopping List for {date_range}"
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                attachments=attachments if include_attachment else None
            )
            
        except Exception as e:
            logger.error(f"Failed to send shopping list: {e}")
            return False

    def send_nutrition_summary(
        self,
        to_email: str,
        target_date: date,
        period: str = "day"
    ) -> bool:
        """
        Send a nutrition summary email for a specific date or period.

        Args:
            to_email: Recipient email address
            target_date: Date for nutrition summary
            period: Period type ('day', 'week', 'month')

        Returns:
            True if email sent successfully
        """
        from .email_templates import EmailTemplateManager

        try:
            # Calculate date range based on period
            if period == "day":
                start_date = end_date = target_date
            elif period == "week":
                # Get start of week (Monday)
                days_since_monday = target_date.weekday()
                start_date = target_date - timedelta(days=days_since_monday)
                end_date = start_date + timedelta(days=6)
            elif period == "month":
                start_date = target_date.replace(day=1)
                if target_date.month == 12:
                    end_date = target_date.replace(year=target_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)
            else:
                raise ValueError(f"Invalid period: {period}")

            # Get meal plans for the period
            meal_plans = MealPlanner.get_plans_for_date_range(
                start_date=start_date,
                end_date=end_date
            )

            if not meal_plans:
                logger.warning(f"No meal plans found for {period} starting {target_date}")
                return False

            # Calculate nutrition summary
            nutrition_data = self._calculate_nutrition_summary(meal_plans)

            template_manager = EmailTemplateManager()
            html_content, text_content = template_manager.render_nutrition_summary(
                start_date=start_date,
                end_date=end_date,
                period=period,
                nutrition_data=nutrition_data,
                meal_plans=meal_plans
            )

            period_str = period.title()
            if period == "day":
                date_str = target_date.strftime('%B %d, %Y')
            elif period == "week":
                date_str = f"Week of {start_date.strftime('%B %d, %Y')}"
            else:  # month
                date_str = target_date.strftime('%B %Y')

            subject = f"Nutrition Summary - {period_str} ({date_str})"

            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )

        except Exception as e:
            logger.error(f"Failed to send nutrition summary: {e}")
            return False

    def send_weekly_meal_plan(
        self,
        to_email: str,
        start_date: date,
        include_shopping_list: bool = True
    ) -> bool:
        """
        Send a weekly meal plan summary email.

        Args:
            to_email: Recipient email address
            start_date: Start date of the week (should be Monday)
            include_shopping_list: Whether to include shopping list

        Returns:
            True if email sent successfully
        """
        from .email_templates import EmailTemplateManager

        try:
            # Ensure start_date is Monday
            days_since_monday = start_date.weekday()
            if days_since_monday != 0:
                start_date = start_date - timedelta(days=days_since_monday)

            end_date = start_date + timedelta(days=6)

            # Get meal plans for the week
            meal_plans = MealPlanner.get_plans_for_date_range(
                start_date=start_date,
                end_date=end_date
            )

            # Generate shopping list if requested
            shopping_list = None
            if include_shopping_list:
                shopping_list = ShoppingListGenerator.generate_from_date_range(
                    start_date=start_date,
                    end_date=end_date
                )

            template_manager = EmailTemplateManager()
            html_content, text_content = template_manager.render_weekly_meal_plan(
                start_date=start_date,
                end_date=end_date,
                meal_plans=meal_plans,
                shopping_list=shopping_list
            )

            # Prepare attachments
            attachments = []
            if shopping_list and shopping_list.items:
                # Add shopping list as attachment
                text_export = ShoppingListExporter.export_to_text(shopping_list)
                attachments.append({
                    'filename': f'weekly_shopping_list_{start_date}.txt',
                    'content': text_export.encode('utf-8')
                })

            subject = f"Weekly Meal Plan - Week of {start_date.strftime('%B %d, %Y')}"

            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                attachments=attachments if attachments else None
            )

        except Exception as e:
            logger.error(f"Failed to send weekly meal plan: {e}")
            return False

    def _calculate_nutrition_summary(self, meal_plans: List[Any]) -> Dict[str, Any]:
        """
        Calculate nutrition summary for a list of meal plans.

        Args:
            meal_plans: List of meal plan objects

        Returns:
            Dictionary containing nutrition summary data
        """
        try:
            total_nutrition = {
                'calories': 0,
                'protein': 0,
                'carbs': 0,
                'fat': 0,
                'fiber': 0,
                'sodium': 0
            }

            recipe_count = 0
            meal_count = len(meal_plans)

            for plan in meal_plans:
                if hasattr(plan, 'recipe') and plan.recipe:
                    recipe_count += 1
                    servings = getattr(plan, 'servings', 1)

                    # Get recipe nutrition (this would integrate with nutritional analysis)
                    recipe_nutrition = {
                        'calories': getattr(plan.recipe, 'calories', 0) or 0,
                        'protein': getattr(plan.recipe, 'protein', 0) or 0,
                        'carbs': getattr(plan.recipe, 'carbs', 0) or 0,
                        'fat': getattr(plan.recipe, 'fat', 0) or 0,
                        'fiber': getattr(plan.recipe, 'fiber', 0) or 0,
                        'sodium': getattr(plan.recipe, 'sodium', 0) or 0
                    }

                    # Add to total (scaled by servings)
                    for nutrient in total_nutrition:
                        total_nutrition[nutrient] += recipe_nutrition[nutrient] * servings

            # Calculate averages
            avg_nutrition = {}
            if meal_count > 0:
                for nutrient in total_nutrition:
                    avg_nutrition[f'avg_{nutrient}'] = total_nutrition[nutrient] / meal_count

            return {
                'total': total_nutrition,
                'average': avg_nutrition,
                'meal_count': meal_count,
                'recipe_count': recipe_count
            }

        except Exception as e:
            logger.error(f"Error calculating nutrition summary: {e}")
            return {
                'total': {},
                'average': {},
                'meal_count': 0,
                'recipe_count': 0
            }
