"""
Tests for the plugin loader module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mealplanner.plugin_loader import PluginLoader, get_plugin_loader, load_plugins


@pytest.fixture
def temp_plugins_dir(tmp_path):
    """Create a temporary plugins directory for testing."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


@pytest.fixture
def sample_plugin_file(temp_plugins_dir):
    """Create a sample plugin file."""
    plugin_file = temp_plugins_dir / "sample_plugin.py"
    plugin_content = '''
def cmd_hello():
    """Sample plugin command."""
    return "Hello from plugin!"

def commands():
    """Return plugin commands."""
    return {
        "greet": lambda: "Greetings!",
        "farewell": lambda: "Goodbye!"
    }

def regular_function():
    """Not a command function."""
    return "regular"
'''
    plugin_file.write_text(plugin_content)
    return plugin_file


@pytest.fixture
def invalid_plugin_file(temp_plugins_dir):
    """Create an invalid plugin file."""
    plugin_file = temp_plugins_dir / "invalid_plugin.py"
    plugin_content = '''
# This will cause a syntax error
def invalid_function(
    return "broken"
'''
    plugin_file.write_text(plugin_content)
    return plugin_file


class TestPluginLoader:
    """Test the PluginLoader class."""
    
    def test_init_default(self):
        """Test PluginLoader initialization with default directory."""
        loader = PluginLoader()
        assert loader.plugins_dir == Path("plugins")
        assert loader.loaded_plugins == {}
    
    def test_init_custom_dir(self):
        """Test PluginLoader initialization with custom directory."""
        loader = PluginLoader("custom_plugins")
        assert loader.plugins_dir == Path("custom_plugins")
    
    def test_discover_plugins_no_directory(self):
        """Test plugin discovery when directory doesn't exist."""
        loader = PluginLoader("nonexistent")
        plugins = loader.discover_plugins()
        assert plugins == []
    
    def test_discover_plugins_empty_directory(self, temp_plugins_dir):
        """Test plugin discovery in empty directory."""
        loader = PluginLoader(str(temp_plugins_dir))
        plugins = loader.discover_plugins()
        assert plugins == []
    
    def test_discover_plugins_with_files(self, temp_plugins_dir, sample_plugin_file):
        """Test plugin discovery with plugin files."""
        # Create additional files
        (temp_plugins_dir / "__init__.py").touch()  # Should be ignored
        (temp_plugins_dir / "_private.py").touch()  # Should be ignored
        (temp_plugins_dir / "another_plugin.py").touch()
        
        loader = PluginLoader(str(temp_plugins_dir))
        plugins = loader.discover_plugins()
        
        plugin_names = [p.stem for p in plugins]
        assert "sample_plugin" in plugin_names
        assert "another_plugin" in plugin_names
        assert "__init__" not in plugin_names
        assert "_private" not in plugin_names
    
    def test_discover_plugins_nested(self, temp_plugins_dir):
        """Test plugin discovery in nested directories."""
        nested_dir = temp_plugins_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "nested_plugin.py").touch()
        
        loader = PluginLoader(str(temp_plugins_dir))
        plugins = loader.discover_plugins()
        
        plugin_names = [p.stem for p in plugins]
        assert "nested_plugin" in plugin_names
    
    def test_load_plugin_success(self, temp_plugins_dir, sample_plugin_file):
        """Test successful plugin loading."""
        loader = PluginLoader(str(temp_plugins_dir))
        plugin_module = loader.load_plugin(sample_plugin_file)
        
        assert hasattr(plugin_module, 'cmd_hello')
        assert hasattr(plugin_module, 'commands')
        assert callable(plugin_module.cmd_hello)
        assert plugin_module.cmd_hello() == "Hello from plugin!"
    
    def test_load_plugin_invalid_syntax(self, temp_plugins_dir, invalid_plugin_file):
        """Test loading plugin with invalid syntax."""
        loader = PluginLoader(str(temp_plugins_dir))
        
        with pytest.raises(ImportError):
            loader.load_plugin(invalid_plugin_file)
    
    def test_load_all_plugins_success(self, temp_plugins_dir, sample_plugin_file):
        """Test loading all plugins successfully."""
        loader = PluginLoader(str(temp_plugins_dir))
        plugins = loader.load_all_plugins()
        
        assert "sample_plugin" in plugins
        assert hasattr(plugins["sample_plugin"], 'cmd_hello')
    
    def test_load_all_plugins_with_failures(self, temp_plugins_dir, sample_plugin_file, invalid_plugin_file):
        """Test loading all plugins with some failures."""
        loader = PluginLoader(str(temp_plugins_dir))
        plugins = loader.load_all_plugins()
        
        # Should load the valid plugin and skip the invalid one
        assert "sample_plugin" in plugins
        assert "invalid_plugin" not in plugins
    
    def test_get_plugin_existing(self, temp_plugins_dir, sample_plugin_file):
        """Test getting an existing plugin."""
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        
        plugin = loader.get_plugin("sample_plugin")
        assert plugin is not None
        assert hasattr(plugin, 'cmd_hello')
    
    def test_get_plugin_nonexistent(self, temp_plugins_dir):
        """Test getting a non-existent plugin."""
        loader = PluginLoader(str(temp_plugins_dir))
        plugin = loader.get_plugin("nonexistent")
        assert plugin is None
    
    def test_get_plugin_commands_cmd_functions(self, temp_plugins_dir, sample_plugin_file):
        """Test getting plugin commands from cmd_ functions."""
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        
        commands = loader.get_plugin_commands()
        assert "sample_plugin_hello" in commands
        assert callable(commands["sample_plugin_hello"])
    
    def test_get_plugin_commands_commands_function(self, temp_plugins_dir, sample_plugin_file):
        """Test getting plugin commands from commands() function."""
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        
        commands = loader.get_plugin_commands()
        assert "sample_plugin_greet" in commands
        assert "sample_plugin_farewell" in commands
        assert callable(commands["sample_plugin_greet"])
    
    def test_get_plugin_commands_empty(self, temp_plugins_dir):
        """Test getting plugin commands when no plugins loaded."""
        loader = PluginLoader(str(temp_plugins_dir))
        commands = loader.get_plugin_commands()
        assert commands == {}


class TestGlobalPluginLoader:
    """Test global plugin loader functions."""
    
    def test_get_plugin_loader(self):
        """Test getting the global plugin loader."""
        loader = get_plugin_loader()
        assert isinstance(loader, PluginLoader)
        assert loader.plugins_dir == Path("plugins")
    
    def test_load_plugins_global(self, temp_plugins_dir, sample_plugin_file):
        """Test loading plugins using global function."""
        # Change the global loader's directory for testing
        global_loader = get_plugin_loader()
        global_loader.plugins_dir = Path(str(temp_plugins_dir))
        
        plugins = load_plugins()
        assert "sample_plugin" in plugins
    
    @patch('mealplanner.plugin_loader._plugin_loader')
    def test_load_plugins_with_mock(self, mock_loader):
        """Test load_plugins function with mocked loader."""
        mock_loader.load_all_plugins.return_value = {"test_plugin": MagicMock()}
        
        plugins = load_plugins()
        assert "test_plugin" in plugins
        mock_loader.load_all_plugins.assert_called_once()


class TestPluginCommandExtraction:
    """Test plugin command extraction functionality."""
    
    def test_commands_attribute_dict(self, temp_plugins_dir):
        """Test plugin with commands attribute as dict."""
        plugin_file = temp_plugins_dir / "dict_commands.py"
        plugin_content = '''
commands = {
    "test": lambda: "test result",
    "another": lambda: "another result"
}
'''
        plugin_file.write_text(plugin_content)
        
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        commands = loader.get_plugin_commands()
        
        assert "dict_commands_test" in commands
        assert "dict_commands_another" in commands
    
    def test_commands_attribute_callable(self, temp_plugins_dir):
        """Test plugin with commands attribute as callable."""
        plugin_file = temp_plugins_dir / "callable_commands.py"
        plugin_content = '''
def commands():
    return {
        "dynamic": lambda: "dynamic result"
    }
'''
        plugin_file.write_text(plugin_content)
        
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        commands = loader.get_plugin_commands()
        
        assert "callable_commands_dynamic" in commands
    
    def test_mixed_command_sources(self, temp_plugins_dir):
        """Test plugin with both cmd_ functions and commands attribute."""
        plugin_file = temp_plugins_dir / "mixed_commands.py"
        plugin_content = '''
def cmd_function_based():
    return "function based"

def commands():
    return {
        "attribute_based": lambda: "attribute based"
    }
'''
        plugin_file.write_text(plugin_content)
        
        loader = PluginLoader(str(temp_plugins_dir))
        loader.load_all_plugins()
        commands = loader.get_plugin_commands()
        
        assert "mixed_commands_function_based" in commands
        assert "mixed_commands_attribute_based" in commands
