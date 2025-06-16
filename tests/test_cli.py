"""
Tests for the CLI module.
"""

import pytest
import sys
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from mealplanner.cli import app, handle_unknown_command
from mealplanner import __version__


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch('mealplanner.cli.init_config') as mock_init, \
         patch('mealplanner.cli.get_config') as mock_get:
        
        mock_config_obj = MagicMock()
        mock_config_obj.debug = False
        mock_get.return_value = mock_config_obj
        
        yield mock_config_obj


@pytest.fixture
def mock_health_check():
    """Mock health check for testing."""
    with patch('mealplanner.cli.run_health_check') as mock_check:
        mock_check.return_value = (True, [])  # Success, no issues
        yield mock_check


@pytest.fixture
def mock_plugins():
    """Mock plugin loading for testing."""
    with patch('mealplanner.cli.load_plugins') as mock_load:
        mock_load.return_value = {}
        yield mock_load


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_help_output(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test that --help shows expected output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Smart Meal Planner" in result.stdout
        assert "meal planning and recipe" in result.stdout
    
    def test_version_flag(self, runner):
        """Test that --version shows the correct version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout
        assert "Smart Meal Planner version" in result.stdout
    
    def test_hello_command(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test the hello command."""
        result = runner.invoke(app, ["hello"])
        assert result.exit_code == 0
        assert "Hello from Smart Meal Planner!" in result.stdout
        assert __version__ in result.stdout


class TestCLIOptions:
    """Test CLI global options."""
    
    def test_debug_flag(self, runner, mock_health_check, mock_plugins):
        """Test that --debug flag is passed to configuration."""
        with patch('mealplanner.cli.init_config') as mock_init, \
             patch('mealplanner.cli.get_config') as mock_get:
            
            mock_config_obj = MagicMock()
            mock_config_obj.debug = True
            mock_get.return_value = mock_config_obj
            
            result = runner.invoke(app, ["--debug", "hello"])
            assert result.exit_code == 0
            mock_init.assert_called_once_with(config_file=None, debug=True)
    
    def test_config_flag_valid_file(self, runner, mock_health_check, mock_plugins, tmp_path):
        """Test --config flag with valid file."""
        config_file = tmp_path / "test.env"
        config_file.write_text("TEST_VAR=test_value")
        
        with patch('mealplanner.cli.init_config') as mock_init, \
             patch('mealplanner.cli.get_config') as mock_get:
            
            mock_config_obj = MagicMock()
            mock_config_obj.debug = False
            mock_get.return_value = mock_config_obj
            
            result = runner.invoke(app, ["--config", str(config_file), "hello"])
            assert result.exit_code == 0
            mock_init.assert_called_once_with(config_file=str(config_file), debug=False)
    
    def test_config_flag_invalid_file(self, runner):
        """Test --config flag with non-existent file."""
        result = runner.invoke(app, ["--config", "nonexistent.env", "hello"])
        assert result.exit_code == 1
        assert "Config file not found" in result.stderr
    
    def test_config_flag_invalid_format(self, runner, tmp_path):
        """Test --config flag with unsupported file format."""
        config_file = tmp_path / "test.txt"
        config_file.write_text("some content")

        result = runner.invoke(app, ["--config", str(config_file), "hello"])
        assert result.exit_code == 1
        assert "Unsupported config file format" in result.stderr


class TestHealthChecks:
    """Test health check integration."""
    
    def test_health_check_failure(self, runner, mock_config, mock_plugins):
        """Test behavior when health checks fail."""
        with patch('mealplanner.cli.run_health_check') as mock_check, \
             patch('mealplanner.cli.create_missing_directories') as mock_create:

            mock_check.return_value = (False, ["Missing directory: tests"])

            result = runner.invoke(app, ["hello"])
            assert result.exit_code == 1
            assert "Health check failed" in result.stderr
            assert "Missing directory: tests" in result.stderr
            mock_create.assert_called_once()
    
    def test_health_check_exception(self, runner, mock_config, mock_plugins):
        """Test behavior when health check raises exception."""
        with patch('mealplanner.cli.run_health_check') as mock_check:
            mock_check.side_effect = Exception("Health check error")

            result = runner.invoke(app, ["hello"])
            assert result.exit_code == 1
            assert "Error during health check" in result.stderr


class TestErrorHandling:
    """Test error handling and unknown commands."""

    def test_handle_unknown_command(self, capsys):
        """Test unknown command handling."""
        handle_unknown_command("nonexistent")
        captured = capsys.readouterr()
        assert "Unknown command 'nonexistent'" in captured.err
        assert "Available commands:" in captured.err
        assert "Use 'mealplanner --help'" in captured.err

    def test_cli_main_with_exception(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test CLI main function with unexpected exception."""
        with patch('mealplanner.cli.app') as mock_app:
            mock_app.side_effect = Exception("Unexpected error")

            from mealplanner.cli import cli_main
            with pytest.raises(SystemExit):
                cli_main()


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_config_file_none(self):
        """Test config file validation with None value."""
        from mealplanner.cli import validate_config_file
        result = validate_config_file(None)
        assert result is None

    def test_validate_config_file_valid_env(self, tmp_path):
        """Test config file validation with valid .env file."""
        from mealplanner.cli import validate_config_file
        config_file = tmp_path / "test.env"
        config_file.write_text("TEST=value")

        result = validate_config_file(str(config_file))
        assert result == str(config_file)

    def test_validate_config_file_no_extension(self, tmp_path):
        """Test config file validation with no extension."""
        from mealplanner.cli import validate_config_file
        config_file = tmp_path / "config"
        config_file.write_text("TEST=value")

        result = validate_config_file(str(config_file))
        assert result == str(config_file)


class TestDatabaseCommands:
    """Test database-related CLI commands."""

    def test_init_db_command_success(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test successful database initialization."""
        with patch('mealplanner.database.init_database') as mock_init_db, \
             patch('mealplanner.database.get_database_info') as mock_db_info:

            mock_db_info.return_value = {
                'database_url': 'sqlite:///test.db',
                'driver': 'sqlite'
            }

            result = runner.invoke(app, ["init-db"])
            assert result.exit_code == 0
            assert "Database initialization completed successfully" in result.stdout
            assert "sqlite:///test.db" in result.stdout
            mock_init_db.assert_called_once_with(database_url=None, force=False)

    def test_init_db_command_with_force(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test database initialization with force flag."""
        with patch('mealplanner.database.init_database') as mock_init_db, \
             patch('mealplanner.database.get_database_info') as mock_db_info:

            mock_db_info.return_value = {
                'database_url': 'sqlite:///test.db',
                'driver': 'sqlite'
            }

            result = runner.invoke(app, ["init-db", "--force"])
            assert result.exit_code == 0
            mock_init_db.assert_called_once_with(database_url=None, force=True)

    def test_init_db_command_with_custom_url(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test database initialization with custom URL."""
        with patch('mealplanner.database.init_database') as mock_init_db, \
             patch('mealplanner.database.get_database_info') as mock_db_info:

            mock_db_info.return_value = {
                'database_url': 'sqlite:///custom.db',
                'driver': 'sqlite'
            }

            result = runner.invoke(app, ["init-db", "--database-url", "sqlite:///custom.db"])
            assert result.exit_code == 0
            mock_init_db.assert_called_once_with(database_url="sqlite:///custom.db", force=False)

    def test_init_db_command_failure(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test database initialization failure."""
        with patch('mealplanner.database.init_database') as mock_init_db:
            from sqlalchemy.exc import OperationalError
            mock_init_db.side_effect = OperationalError("Database error", None, None)

            result = runner.invoke(app, ["init-db"])
            assert result.exit_code == 1
            assert "Database initialization failed" in result.stderr

    def test_db_info_command_success(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test successful database info command."""
        with patch('mealplanner.database.get_database_info') as mock_db_info:
            mock_db_info.return_value = {
                'database_url': 'sqlite:///test.db',
                'driver': 'sqlite',
                'connected': True,
                'database_file': 'test.db',
                'file_exists': True,
                'file_size': 1024
            }

            result = runner.invoke(app, ["db-info"])
            assert result.exit_code == 0
            assert "Database Information" in result.stdout
            assert "sqlite:///test.db" in result.stdout
            assert "Driver: sqlite" in result.stdout
            assert "Connected: ✅ Yes" in result.stdout
            assert "Database file: test.db" in result.stdout

    def test_db_info_command_error(self, runner, mock_config, mock_health_check, mock_plugins):
        """Test database info command with error."""
        with patch('mealplanner.database.get_database_info') as mock_db_info:
            mock_db_info.return_value = {'error': 'Database connection failed'}

            result = runner.invoke(app, ["db-info"])
            assert result.exit_code == 1
            assert "Error getting database info" in result.stderr
