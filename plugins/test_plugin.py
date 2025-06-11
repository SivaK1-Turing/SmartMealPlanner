"""
Test plugin for demonstrating the plugin system.
"""

def cmd_test():
    """A test command from the plugin."""
    return "Test plugin command works!"

def cmd_greet():
    """A greeting command from the plugin."""
    return "Hello from the test plugin!"

def commands():
    """Return additional commands as a dictionary."""
    return {
        "farewell": lambda: "Goodbye from test plugin!",
        "status": lambda: "Plugin is active"
    }
