"""
Configuration management for the Smart Meal Planner application.

Handles environment variables, configuration files, and logging setup.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Optional yaml import - will be available if PyYAML is installed
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_file: Optional[str] = None, debug: bool = False):
        """
        Initialize configuration.
        
        Args:
            config_file: Optional path to configuration file (.env or .yaml)
            debug: Enable debug logging
        """
        self.debug = debug
        self.config_file = config_file
        self._load_config()
        self._setup_logging()
    
    def _load_config(self):
        """Load configuration from environment variables and config files."""
        # Load default .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load custom config file if specified
        if self.config_file:
            config_path = Path(self.config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {self.config_file}")
            
            if config_path.suffix.lower() in ['.env'] or config_path.suffix == '':
                # Treat files without extension as .env files
                load_dotenv(config_path)
            elif config_path.suffix.lower() in ['.yaml', '.yml']:
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML is required for YAML config files. Install with: pip install PyYAML")
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    # Set environment variables from YAML
                    for key, value in config_data.items():
                        os.environ[key] = str(value)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
    
    def _setup_logging(self):
        """Setup JSON-formatted logging with adjustable verbosity."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        # Create custom formatter for JSON output
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler with JSON formatter
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(console_handler)
        
        # Set specific logger levels
        logging.getLogger("mealplanner").setLevel(log_level)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value from environment variables."""
        return os.getenv(key, default)
    
    def get_required(self, key: str) -> str:
        """Get required configuration value, raise error if not found."""
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable not set: {key}")
        return value


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call init_config() first.")
    return _config


def init_config(config_file: Optional[str] = None, debug: bool = False) -> Config:
    """Initialize the global configuration."""
    global _config
    _config = Config(config_file=config_file, debug=debug)
    return _config
