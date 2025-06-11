"""
Command-line interface for the Smart Meal Planner application.

Provides the main CLI using Typer with global options and command management.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from typer import Typer

from . import __version__
from .config import init_config, get_config
from .health import run_health_check, create_missing_directories
from .plugin_loader import load_plugins

logger = logging.getLogger(__name__)

# Create the main Typer app
app = Typer(
    name="mealplanner",
    help="Smart Meal Planner - A command-line application for meal planning and recipe management",
    add_completion=False,
    rich_markup_mode="rich"
)


def version_callback(value: bool):
    """Callback for --version flag."""
    if value:
        typer.echo(f"Smart Meal Planner version {__version__}")
        raise typer.Exit()


def validate_config_file(value: Optional[str]) -> Optional[str]:
    """Validate that config file exists if provided."""
    if value is not None:
        config_path = Path(value)
        if not config_path.exists():
            print(f"Error: Config file not found: {value}", file=sys.stderr)
            raise typer.Exit(1)
        if config_path.suffix.lower() not in ['.env', '.yaml', '.yml', '']:
            print(f"Error: Unsupported config file format: {config_path.suffix}", file=sys.stderr)
            raise typer.Exit(1)
    return value


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, 
        "--version", 
        callback=version_callback,
        help="Show version and exit"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging with JSON format"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to alternate configuration file (.env or .yaml)",
        callback=validate_config_file
    )
):
    """
    Smart Meal Planner - A command-line application for meal planning and recipe management.
    
    This application helps you import, organize, and schedule recipes into weekly meal plans.
    It offers ingredient-based search, nutritional analysis, shopping list export, and 
    automated email reminders.
    """
    # Initialize configuration
    try:
        init_config(config_file=config, debug=debug)
        logger.info("Configuration initialized successfully")
    except Exception as e:
        typer.echo(f"Error initializing configuration: {e}", err=True)
        raise typer.Exit(1)
    
    # Run health checks
    try:
        success, issues = run_health_check()
        if not success:
            print("Health check failed:", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)

            # Try to create missing directories
            try:
                create_missing_directories()
                print("Created missing directories. Please run the command again.")
            except Exception as create_error:
                print(f"Failed to create missing directories: {create_error}", file=sys.stderr)

            raise typer.Exit(1)
    except Exception as e:
        print(f"Error during health check: {e}", file=sys.stderr)
        raise typer.Exit(1)
    
    # Load plugins
    try:
        plugins = load_plugins()
        if plugins:
            logger.info(f"Loaded {len(plugins)} plugins")
        else:
            logger.info("No plugins found")
    except Exception as e:
        logger.warning(f"Error loading plugins: {e}")


@app.command()
def hello():
    """
    A simple hello command to test the CLI setup.
    
    This is a placeholder command for Feature 1 testing.
    """
    config = get_config()
    typer.echo("Hello from Smart Meal Planner!")
    typer.echo(f"Version: {__version__}")
    typer.echo(f"Debug mode: {config.debug}")
    
    if config.debug:
        logger.info("Hello command executed successfully")


def handle_unknown_command(command_name: str):
    """
    Handle unknown commands by suggesting valid subcommands.
    
    Args:
        command_name: The unknown command that was attempted
    """
    typer.echo(f"Error: Unknown command '{command_name}'", err=True)
    typer.echo("\nAvailable commands:", err=True)
    
    # Get available commands from the app
    commands = []
    if hasattr(app, 'registered_commands'):
        if isinstance(app.registered_commands, dict):
            for command in app.registered_commands.values():
                commands.append(command.name)
        elif isinstance(app.registered_commands, list):
            for command in app.registered_commands:
                if hasattr(command, 'name'):
                    commands.append(command.name)

    # Also check for commands in the app.commands list
    if hasattr(app, 'commands') and isinstance(app.commands, dict):
        commands.extend(app.commands.keys())

    if commands:
        for cmd in sorted(set(commands)):  # Remove duplicates
            typer.echo(f"  {cmd}", err=True)
    else:
        typer.echo("  hello", err=True)  # At least show the hello command
    
    typer.echo("\nUse 'mealplanner --help' for more information.", err=True)


def cli_main():
    """
    Main entry point for the CLI application.
    
    This function handles unknown commands gracefully and provides helpful error messages.
    """
    try:
        app()
    except typer.Exit as e:
        # Re-raise typer exits
        raise e
    except Exception as e:
        # Handle unexpected errors
        typer.echo(f"Unexpected error: {e}", err=True)
        logger.exception("Unexpected error in CLI")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
