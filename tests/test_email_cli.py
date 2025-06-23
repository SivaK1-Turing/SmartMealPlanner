"""
Tests for email CLI commands.

Tests CLI commands for email functionality including test email, meal reminders,
shopping list emails, nutrition summaries, and weekly meal plans.
"""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from datetime import date

from mealplanner.cli import app
from mealplanner.email_notifications import EmailConfigurationError, EmailSendError


class TestEmailCLICommands:
    """Test cases for email CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_test_email_success(self, mock_email_manager):
        """Test successful email configuration test."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.test_connection.return_value = True
        mock_manager.send_email.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, ['test-email', 'test@example.com'])
        
        assert result.exit_code == 0
        assert "Testing email configuration" in result.stdout
        assert "SMTP connection successful" in result.stdout
        assert "Test email sent successfully" in result.stdout
        
        mock_manager.test_connection.assert_called_once()
        mock_manager.send_email.assert_called_once()
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_test_email_connection_failure(self, mock_email_manager):
        """Test email test with connection failure."""
        # Mock failed connection
        mock_manager = Mock()
        mock_manager.test_connection.return_value = False
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, ['test-email', 'test@example.com'])
        
        assert result.exit_code == 1
        assert "SMTP connection test failed" in result.stdout
        assert "Please check your email configuration" in result.stdout
        
        mock_manager.test_connection.assert_called_once()
        mock_manager.send_email.assert_not_called()
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_test_email_send_failure(self, mock_email_manager):
        """Test email test with send failure."""
        # Mock successful connection but failed send
        mock_manager = Mock()
        mock_manager.test_connection.return_value = True
        mock_manager.send_email.return_value = False
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, ['test-email', 'test@example.com'])
        
        assert result.exit_code == 1
        assert "SMTP connection successful" in result.stdout
        assert "Failed to send test email" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_test_email_configuration_error(self, mock_email_manager):
        """Test email test with configuration error."""
        # Mock configuration error
        mock_email_manager.side_effect = EmailConfigurationError("Missing SMTP settings")
        
        result = self.runner.invoke(app, ['test-email', 'test@example.com'])
        
        assert result.exit_code == 1
        assert "Email configuration error" in result.stdout
        assert "Missing SMTP settings" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_meal_reminder_success(self, mock_email_manager):
        """Test successful meal reminder sending."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_meal_reminder.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-meal-reminder',
            'test@example.com',
            '2024-01-15'
        ])
        
        assert result.exit_code == 0
        assert "Sending meal reminder for 2024-01-15" in result.stdout
        assert "Meal reminder sent successfully" in result.stdout
        
        mock_manager.send_meal_reminder.assert_called_once_with(
            to_email='test@example.com',
            target_date=date(2024, 1, 15)
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_meal_reminder_invalid_date(self, mock_email_manager):
        """Test meal reminder with invalid date format."""
        result = self.runner.invoke(app, [
            'send-meal-reminder',
            'test@example.com',
            'invalid-date'
        ])
        
        assert result.exit_code == 1
        assert "Invalid date format" in result.stdout
        assert "Use YYYY-MM-DD" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_meal_reminder_send_failure(self, mock_email_manager):
        """Test meal reminder with send failure."""
        # Mock failed send
        mock_manager = Mock()
        mock_manager.send_meal_reminder.return_value = False
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-meal-reminder',
            'test@example.com',
            '2024-01-15'
        ])
        
        assert result.exit_code == 1
        assert "Failed to send meal reminder" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_shopping_list_email_success(self, mock_email_manager):
        """Test successful shopping list email sending."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_shopping_list.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-shopping-list-email',
            'test@example.com',
            '2024-01-15',
            '--end-date', '2024-01-16'
        ])
        
        assert result.exit_code == 0
        assert "Sending shopping list for 2024-01-15 to 2024-01-16" in result.stdout
        assert "Shopping list sent successfully" in result.stdout
        assert "Included attachments" in result.stdout
        
        mock_manager.send_shopping_list.assert_called_once_with(
            to_email='test@example.com',
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 16),
            include_attachment=True
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_shopping_list_email_no_attachments(self, mock_email_manager):
        """Test shopping list email without attachments."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_shopping_list.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-shopping-list-email',
            'test@example.com',
            '2024-01-15',
            '--no-attachments'
        ])
        
        assert result.exit_code == 0
        assert "Shopping list sent successfully" in result.stdout
        assert "Included attachments" not in result.stdout
        
        mock_manager.send_shopping_list.assert_called_once_with(
            to_email='test@example.com',
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            include_attachment=False
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_shopping_list_email_invalid_date_range(self, mock_email_manager):
        """Test shopping list email with invalid date range."""
        result = self.runner.invoke(app, [
            'send-shopping-list-email',
            'test@example.com',
            '2024-01-16',
            '--end-date', '2024-01-15'
        ])
        
        assert result.exit_code == 1
        assert "End date must be after start date" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_nutrition_summary_email_success(self, mock_email_manager):
        """Test successful nutrition summary email sending."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_nutrition_summary.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-nutrition-summary-email',
            'test@example.com',
            '2024-01-15',
            '--period', 'week'
        ])
        
        assert result.exit_code == 0
        assert "Sending nutrition summary (week) for 2024-01-15" in result.stdout
        assert "Nutrition summary sent successfully" in result.stdout
        
        mock_manager.send_nutrition_summary.assert_called_once_with(
            to_email='test@example.com',
            target_date=date(2024, 1, 15),
            period='week'
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_nutrition_summary_email_invalid_period(self, mock_email_manager):
        """Test nutrition summary email with invalid period."""
        result = self.runner.invoke(app, [
            'send-nutrition-summary-email',
            'test@example.com',
            '2024-01-15',
            '--period', 'invalid'
        ])
        
        assert result.exit_code == 1
        assert "Invalid period" in result.stdout
        assert "Use: day, week, or month" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_weekly_meal_plan_email_success(self, mock_email_manager):
        """Test successful weekly meal plan email sending."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_weekly_meal_plan.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-weekly-meal-plan-email',
            'test@example.com',
            '2024-01-15',
            '--shopping-list'
        ])
        
        assert result.exit_code == 0
        assert "Sending weekly meal plan starting 2024-01-15" in result.stdout
        assert "Weekly meal plan sent successfully" in result.stdout
        assert "Included shopping list attachment" in result.stdout
        
        mock_manager.send_weekly_meal_plan.assert_called_once_with(
            to_email='test@example.com',
            start_date=date(2024, 1, 15),
            include_shopping_list=True
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_send_weekly_meal_plan_email_no_shopping_list(self, mock_email_manager):
        """Test weekly meal plan email without shopping list."""
        # Mock successful email manager
        mock_manager = Mock()
        mock_manager.send_weekly_meal_plan.return_value = True
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-weekly-meal-plan-email',
            'test@example.com',
            '2024-01-15',
            '--no-shopping-list'
        ])
        
        assert result.exit_code == 0
        assert "Weekly meal plan sent successfully" in result.stdout
        assert "Included shopping list attachment" not in result.stdout
        
        mock_manager.send_weekly_meal_plan.assert_called_once_with(
            to_email='test@example.com',
            start_date=date(2024, 1, 15),
            include_shopping_list=False
        )
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_email_send_error_handling(self, mock_email_manager):
        """Test email send error handling."""
        # Mock email send error
        mock_manager = Mock()
        mock_manager.send_meal_reminder.side_effect = EmailSendError("SMTP connection failed")
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-meal-reminder',
            'test@example.com',
            '2024-01-15'
        ])
        
        assert result.exit_code == 1
        assert "Failed to send email" in result.stdout
        assert "SMTP connection failed" in result.stdout
    
    @patch('mealplanner.cli.EmailNotificationManager')
    def test_email_configuration_error_handling(self, mock_email_manager):
        """Test email configuration error handling."""
        # Mock configuration error
        mock_manager = Mock()
        mock_manager.send_shopping_list.side_effect = EmailConfigurationError("Missing SMTP host")
        mock_email_manager.return_value = mock_manager
        
        result = self.runner.invoke(app, [
            'send-shopping-list-email',
            'test@example.com',
            '2024-01-15'
        ])
        
        assert result.exit_code == 1
        assert "Email configuration error" in result.stdout
        assert "Missing SMTP host" in result.stdout
