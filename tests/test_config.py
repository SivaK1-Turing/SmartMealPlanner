"""
Tests for the configuration module.
"""

import json
import logging
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from mealplanner.config import Config, init_config, get_config


@pytest.fixture
def clean_env():
    """Clean environment variables for testing."""
    original_env = os.environ.copy()
    # Clear any existing environment variables that might interfere
    for key in list(os.environ.keys()):
        if key.startswith('TEST_'):
            del os.environ[key]
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR=test_value\nANOTHER_VAR=another_value")
    return env_file


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "config.yaml"
    yaml_content = """
TEST_VAR: yaml_value
YAML_SPECIFIC: yaml_only
"""
    yaml_file.write_text(yaml_content)
    return yaml_file


class TestConfig:
    """Test the Config class."""
    
    def test_init_default(self, clean_env):
        """Test Config initialization with defaults."""
        config = Config()
        assert config.debug is False
        assert config.config_file is None
    
    def test_init_with_debug(self, clean_env):
        """Test Config initialization with debug enabled."""
        config = Config(debug=True)
        assert config.debug is True
    
    def test_load_env_file(self, clean_env, temp_env_file):
        """Test loading from .env file."""
        # Change to the directory containing the .env file
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_env_file.parent)
            config = Config()
            assert os.getenv('TEST_VAR') == 'test_value'
            assert os.getenv('ANOTHER_VAR') == 'another_value'
        finally:
            os.chdir(original_cwd)
    
    def test_load_custom_env_file(self, clean_env, temp_env_file):
        """Test loading from custom .env file."""
        config = Config(config_file=str(temp_env_file))
        assert os.getenv('TEST_VAR') == 'test_value'
        assert os.getenv('ANOTHER_VAR') == 'another_value'
    
    @patch('mealplanner.config.YAML_AVAILABLE', True)
    def test_load_yaml_file(self, clean_env, temp_yaml_file):
        """Test loading from YAML file."""
        with patch('yaml.safe_load') as mock_yaml:
            mock_yaml.return_value = {'TEST_VAR': 'yaml_value', 'YAML_SPECIFIC': 'yaml_only'}
            
            config = Config(config_file=str(temp_yaml_file))
            assert os.getenv('TEST_VAR') == 'yaml_value'
            assert os.getenv('YAML_SPECIFIC') == 'yaml_only'
    
    @patch('mealplanner.config.YAML_AVAILABLE', False)
    def test_load_yaml_file_unavailable(self, clean_env, temp_yaml_file):
        """Test loading YAML file when PyYAML is not available."""
        with pytest.raises(ImportError, match="PyYAML is required"):
            Config(config_file=str(temp_yaml_file))
    
    def test_load_nonexistent_file(self, clean_env):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            Config(config_file="nonexistent.env")
    
    def test_load_unsupported_format(self, clean_env, tmp_path):
        """Test loading unsupported config file format."""
        unsupported_file = tmp_path / "config.txt"
        unsupported_file.write_text("some content")
        
        with pytest.raises(ValueError, match="Unsupported config file format"):
            Config(config_file=str(unsupported_file))
    
    def test_get_existing_var(self, clean_env):
        """Test getting existing environment variable."""
        os.environ['TEST_VAR'] = 'test_value'
        config = Config()
        assert config.get('TEST_VAR') == 'test_value'
    
    def test_get_nonexistent_var(self, clean_env):
        """Test getting non-existent environment variable."""
        config = Config()
        assert config.get('NONEXISTENT_VAR') is None
    
    def test_get_with_default(self, clean_env):
        """Test getting variable with default value."""
        config = Config()
        assert config.get('NONEXISTENT_VAR', 'default') == 'default'
    
    def test_get_required_existing(self, clean_env):
        """Test getting required existing variable."""
        os.environ['REQUIRED_VAR'] = 'required_value'
        config = Config()
        assert config.get_required('REQUIRED_VAR') == 'required_value'
    
    def test_get_required_missing(self, clean_env):
        """Test getting required missing variable."""
        config = Config()
        with pytest.raises(ValueError, match="Required environment variable not set"):
            config.get_required('MISSING_REQUIRED_VAR')


class TestLogging:
    """Test logging configuration."""
    
    def test_json_formatter(self, clean_env, caplog):
        """Test JSON logging formatter."""
        config = Config(debug=True)
        
        # Create a test logger and log a message
        test_logger = logging.getLogger('test_logger')
        test_logger.info('Test message')
        
        # Check that logging is configured (we can't easily test JSON format in caplog)
        assert logging.getLogger().level == logging.DEBUG
    
    def test_debug_logging_level(self, clean_env):
        """Test that debug mode sets DEBUG level."""
        config = Config(debug=True)
        assert logging.getLogger().level == logging.DEBUG
    
    def test_normal_logging_level(self, clean_env):
        """Test that normal mode sets INFO level."""
        config = Config(debug=False)
        assert logging.getLogger().level == logging.INFO


class TestGlobalConfig:
    """Test global configuration functions."""
    
    def test_init_config(self, clean_env):
        """Test global config initialization."""
        config = init_config(debug=True)
        assert config.debug is True
        assert get_config() is config
    
    def test_get_config_not_initialized(self, clean_env):
        """Test getting config before initialization."""
        # Reset global config
        import mealplanner.config
        mealplanner.config._config = None
        
        with pytest.raises(RuntimeError, match="Configuration not initialized"):
            get_config()
    
    def test_init_config_with_file(self, clean_env, temp_env_file):
        """Test global config initialization with file."""
        config = init_config(config_file=str(temp_env_file), debug=False)
        assert config.config_file == str(temp_env_file)
        assert config.debug is False


class TestJSONFormatter:
    """Test the JSON formatter functionality."""

    def test_json_formatter_with_exception(self, clean_env):
        """Test JSON formatter with exception information."""
        from mealplanner.config import Config

        # Create a config to set up logging
        config = Config(debug=True)

        # Get the JSON formatter
        logger = logging.getLogger('test_exception')

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Test message with exception")

        # The test passes if no exception is raised during logging
        assert True

    def test_json_formatter_format_time(self, clean_env):
        """Test JSON formatter formatTime method."""
        from mealplanner.config import Config

        config = Config(debug=True)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Get the formatter from the handler
        handler = logging.getLogger().handlers[0]
        formatted = handler.formatter.format(record)

        # Should be valid JSON
        import json
        parsed = json.loads(formatted)
        assert "timestamp" in parsed
        assert "message" in parsed
        assert parsed["message"] == "Test message"


class TestConfigEdgeCases:
    """Test edge cases in configuration."""

    def test_config_with_yaml_dict_values(self, clean_env, tmp_path):
        """Test YAML config with complex dictionary values."""
        yaml_file = tmp_path / "complex.yaml"
        yaml_content = """
database:
  host: localhost
  port: 5432
nested_value: "string_value"
"""
        yaml_file.write_text(yaml_content)

        with patch('mealplanner.config.YAML_AVAILABLE', True):
            with patch('yaml.safe_load') as mock_yaml:
                mock_yaml.return_value = {
                    'database': {'host': 'localhost', 'port': 5432},
                    'nested_value': 'string_value'
                }

                config = Config(config_file=str(yaml_file))
                # Should convert complex values to strings
                assert os.getenv('database') == "{'host': 'localhost', 'port': 5432}"
                assert os.getenv('nested_value') == 'string_value'
