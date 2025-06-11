"""
Dynamic plugin loading functionality for the Smart Meal Planner application.

Discovers and loads Python modules from the plugins/ directory at runtime.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PluginLoader:
    """Handles dynamic loading of plugins from the plugins directory."""
    
    def __init__(self, plugins_dir: str = "plugins"):
        """
        Initialize the plugin loader.
        
        Args:
            plugins_dir: Directory to search for plugins
        """
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, Any] = {}
    
    def discover_plugins(self) -> List[Path]:
        """
        Discover all Python files in the plugins directory.
        
        Returns:
            List of plugin file paths
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            return []
        
        plugin_files = []
        for file_path in self.plugins_dir.rglob("*.py"):
            # Skip __init__.py and files starting with underscore
            if file_path.name == "__init__.py" or file_path.name.startswith("_"):
                continue
            plugin_files.append(file_path)
        
        logger.info(f"Discovered {len(plugin_files)} plugin files")
        return plugin_files
    
    def load_plugin(self, plugin_path: Path) -> Any:
        """
        Load a single plugin from a file path.
        
        Args:
            plugin_path: Path to the plugin file
            
        Returns:
            Loaded plugin module
            
        Raises:
            ImportError: If plugin cannot be loaded
        """
        plugin_name = plugin_path.stem
        
        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create spec for plugin: {plugin_path}")
            
            # Load the module
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return module
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise ImportError(f"Failed to load plugin {plugin_name}: {e}")
    
    def load_all_plugins(self) -> Dict[str, Any]:
        """
        Load all discovered plugins.
        
        Returns:
            Dictionary mapping plugin names to loaded modules
        """
        plugin_files = self.discover_plugins()
        
        for plugin_path in plugin_files:
            plugin_name = plugin_path.stem
            try:
                plugin_module = self.load_plugin(plugin_path)
                self.loaded_plugins[plugin_name] = plugin_module
            except ImportError as e:
                logger.warning(f"Skipping plugin {plugin_name}: {e}")
                continue
        
        logger.info(f"Loaded {len(self.loaded_plugins)} plugins successfully")
        return self.loaded_plugins
    
    def get_plugin(self, plugin_name: str) -> Any:
        """
        Get a loaded plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin module or None if not found
        """
        return self.loaded_plugins.get(plugin_name)
    
    def get_plugin_commands(self) -> Dict[str, Any]:
        """
        Get CLI commands from all loaded plugins.
        
        Returns:
            Dictionary mapping command names to command functions
        """
        commands = {}
        
        for plugin_name, plugin_module in self.loaded_plugins.items():
            # Look for a 'commands' attribute or function
            if hasattr(plugin_module, 'commands'):
                plugin_commands = plugin_module.commands
                if callable(plugin_commands):
                    plugin_commands = plugin_commands()
                
                if isinstance(plugin_commands, dict):
                    for cmd_name, cmd_func in plugin_commands.items():
                        full_cmd_name = f"{plugin_name}_{cmd_name}"
                        commands[full_cmd_name] = cmd_func
                        logger.debug(f"Registered plugin command: {full_cmd_name}")
            
            # Look for individual command functions (functions starting with 'cmd_')
            for attr_name in dir(plugin_module):
                if attr_name.startswith('cmd_') and callable(getattr(plugin_module, attr_name)):
                    cmd_name = attr_name[4:]  # Remove 'cmd_' prefix
                    full_cmd_name = f"{plugin_name}_{cmd_name}"
                    commands[full_cmd_name] = getattr(plugin_module, attr_name)
                    logger.debug(f"Registered plugin command: {full_cmd_name}")
        
        return commands


# Global plugin loader instance
_plugin_loader: PluginLoader = PluginLoader()


def get_plugin_loader() -> PluginLoader:
    """Get the global plugin loader instance."""
    return _plugin_loader


def load_plugins() -> Dict[str, Any]:
    """Load all plugins using the global plugin loader."""
    return _plugin_loader.load_all_plugins()
