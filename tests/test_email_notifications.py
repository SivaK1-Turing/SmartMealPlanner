"""
Tests for email notification functionality.

Tests email sending, SMTP configuration, template rendering, and CLI commands.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import smtplib
from email.mime.multipart import MIMEMultipart

from mealplanner.email_notifications import (
    EmailNotificationManager,
    EmailConfigurationError,
    EmailSendError
)
from mealplanner.models import Plan, Recipe, MealType


class TestEmailNotificationManager:
    """Test cases for EmailNotificationManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.get.side_effect = lambda key, default=None: {
            'SMTP_HOST': 'smtp.test.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@test.com',
            'SMTP_PASSWORD': 'testpass',
            'SMTP_USE_TLS': 'true',
            'SMTP_FROM_NAME': 'Test Meal Planner',
            'SMTP_FROM_EMAIL': 'test@test.com'
        }.get(key, default)
    
    @patch('mealplanner.email_notifications.get_config')
    def test_email_manager_initialization(self, mock_get_config):
        """Test EmailNotificationManager initialization."""
        mock_get_config.return_value = self.mock_config
        
        manager = EmailNotificationManager()
        
        assert manager.config == self.mock_config
        assert manager._smtp_config is None
    
    @patch('mealplanner.email_notifications.get_config')
    def test_get_smtp_config(self, mock_get_config):
        """Test SMTP configuration retrieval."""
        mock_get_config.return_value = self.mock_config
        
        manager = EmailNotificationManager()
        smtp_config = manager._get_smtp_config()
        
        assert smtp_config['host'] == 'smtp.test.com'
        assert smtp_config['port'] == 587
        assert smtp_config['username'] == 'test@test.com'
        assert smtp_config['password'] == 'testpass'
        assert smtp_config['use_tls'] is True
        assert smtp_config['from_name'] == 'Test Meal Planner'
        assert smtp_config['from_email'] == 'test@test.com'
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp, mock_get_config):
        """Test successful SMTP connection test."""
        mock_get_config.return_value = self.mock_config
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        manager = EmailNotificationManager()
        result = manager.test_connection()
        
        assert result is True
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_test_connection_failure(self, mock_smtp, mock_get_config):
        """Test SMTP connection test failure."""
        mock_get_config.return_value = self.mock_config
        mock_smtp.side_effect = smtplib.SMTPException("Connection failed")
        
        manager = EmailNotificationManager()
        result = manager.test_connection()
        
        assert result is False
    
    @patch('mealplanner.email_notifications.get_config')
    def test_test_connection_missing_config(self, mock_get_config):
        """Test SMTP connection test with missing configuration."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'SMTP_HOST': None,
            'SMTP_PORT': '587',
            'SMTP_USERNAME': None,
            'SMTP_PASSWORD': None
        }.get(key, default)
        mock_get_config.return_value = mock_config
        
        manager = EmailNotificationManager()
        result = manager.test_connection()
        
        assert result is False
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, mock_get_config):
        """Test successful email sending."""
        mock_get_config.return_value = self.mock_config
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        manager = EmailNotificationManager()
        
        result = manager.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text"
        )
        
        assert result is True
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.send_message.assert_called_once()
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_send_email_with_attachments(self, mock_smtp, mock_get_config):
        """Test email sending with attachments."""
        mock_get_config.return_value = self.mock_config
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        manager = EmailNotificationManager()
        
        attachments = [
            {'filename': 'test.txt', 'content': b'test content'},
            {'filename': 'test.csv', 'content': b'csv,content'}
        ]
        
        result = manager.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            attachments=attachments
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_send_email_with_cc_bcc(self, mock_smtp, mock_get_config):
        """Test email sending with CC and BCC recipients."""
        mock_get_config.return_value = self.mock_config
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        manager = EmailNotificationManager()
        
        result = manager.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            cc_emails=["cc@test.com"],
            bcc_emails=["bcc@test.com"]
        )
        
        assert result is True
        # Verify that send_message was called with all recipients
        call_args = mock_server.send_message.call_args
        assert call_args is not None
    
    @patch('mealplanner.email_notifications.get_config')
    def test_send_email_missing_config(self, mock_get_config):
        """Test email sending with missing configuration."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'SMTP_HOST': None,
            'SMTP_PORT': '587',
            'SMTP_USERNAME': None,
            'SMTP_PASSWORD': None
        }.get(key, default)
        mock_get_config.return_value = mock_config

        manager = EmailNotificationManager()

        with pytest.raises(EmailSendError):
            manager.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<h1>Test HTML</h1>"
            )
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.smtplib.SMTP')
    def test_send_email_smtp_failure(self, mock_smtp, mock_get_config):
        """Test email sending with SMTP failure."""
        mock_get_config.return_value = self.mock_config
        mock_smtp.side_effect = smtplib.SMTPException("SMTP Error")
        
        manager = EmailNotificationManager()
        
        with pytest.raises(EmailSendError):
            manager.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<h1>Test HTML</h1>"
            )
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.MealPlanner')
    @patch('mealplanner.email_notifications.EmailTemplateManager')
    @patch.object(EmailNotificationManager, 'send_email')
    def test_send_meal_reminder(self, mock_send_email, mock_template_manager, mock_meal_manager, mock_get_config):
        """Test sending meal reminder email."""
        mock_get_config.return_value = self.mock_config
        
        # Mock meal plans
        mock_plan = Mock()
        mock_plan.meal_type = MealType.BREAKFAST
        mock_plan.recipe.name = "Test Recipe"
        mock_plan.servings = 2
        mock_meal_manager.get_plans_for_date_range.return_value = [mock_plan]
        
        # Mock template rendering
        mock_template_instance = Mock()
        mock_template_instance.render_meal_reminder.return_value = ("<html>Test</html>", "Test text")
        mock_template_manager.return_value = mock_template_instance
        
        # Mock successful email sending
        mock_send_email.return_value = True
        
        manager = EmailNotificationManager()
        result = manager.send_meal_reminder(
            to_email="test@test.com",
            target_date=date(2024, 1, 15)
        )
        
        assert result is True
        mock_meal_manager.get_plans_for_date_range.assert_called_once()
        mock_template_instance.render_meal_reminder.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.ShoppingListGenerator')
    @patch('mealplanner.email_notifications.ShoppingListExporter')
    @patch('mealplanner.email_notifications.EmailTemplateManager')
    @patch.object(EmailNotificationManager, 'send_email')
    def test_send_shopping_list(self, mock_send_email, mock_template_manager, mock_exporter, mock_generator, mock_get_config):
        """Test sending shopping list email."""
        mock_get_config.return_value = self.mock_config
        
        # Mock shopping list
        mock_shopping_list = Mock()
        mock_shopping_list.items = [Mock()]  # Non-empty items
        mock_generator.generate_from_date_range.return_value = mock_shopping_list
        
        # Mock exports
        mock_exporter.export_to_text.return_value = "Text export"
        mock_exporter.export_to_csv.return_value = "CSV export"
        
        # Mock template rendering
        mock_template_instance = Mock()
        mock_template_instance.render_shopping_list.return_value = ("<html>Shopping</html>", "Shopping text")
        mock_template_manager.return_value = mock_template_instance
        
        # Mock successful email sending
        mock_send_email.return_value = True
        
        manager = EmailNotificationManager()
        result = manager.send_shopping_list(
            to_email="test@test.com",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 16)
        )
        
        assert result is True
        mock_generator.generate_from_date_range.assert_called_once()
        mock_template_instance.render_shopping_list.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch('mealplanner.email_notifications.get_config')
    @patch('mealplanner.email_notifications.ShoppingListGenerator')
    def test_send_shopping_list_empty(self, mock_generator, mock_get_config):
        """Test sending shopping list email with empty shopping list."""
        mock_get_config.return_value = self.mock_config
        
        # Mock empty shopping list
        mock_shopping_list = Mock()
        mock_shopping_list.items = []  # Empty items
        mock_generator.generate_from_date_range.return_value = mock_shopping_list
        
        manager = EmailNotificationManager()
        result = manager.send_shopping_list(
            to_email="test@test.com",
            start_date=date(2024, 1, 15)
        )
        
        assert result is False
