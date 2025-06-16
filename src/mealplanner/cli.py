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


@app.command()
def init_db(
    force: bool = typer.Option(
        False,
        "--force",
        help="Force initialization by dropping existing tables"
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="Override database URL from configuration"
    )
):
    """
    Initialize or upgrade the database schema.

    Creates all necessary tables and sets up the database for first use.
    Use --force to drop existing tables and recreate them.
    """
    from .database import init_database, get_database_info, OperationalError

    config = get_config()

    try:
        typer.echo("Initializing database...")
        if config.debug:
            logger.info(f"Database initialization started (force={force})")

        # Initialize the database
        init_database(database_url=database_url, force=force)

        # Get database info for confirmation
        db_info = get_database_info()

        typer.echo("✅ Database initialization completed successfully!")
        typer.echo(f"Database: {db_info.get('database_url', 'Unknown')}")
        typer.echo(f"Driver: {db_info.get('driver', 'Unknown')}")

        if config.debug:
            logger.info("Database initialization completed successfully")

    except OperationalError as e:
        typer.echo(f"❌ Database initialization failed: {e}", err=True)
        if config.debug:
            logger.error(f"Database initialization failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error during database initialization: {e}", err=True)
        if config.debug:
            logger.exception("Unexpected error during database initialization")
        raise typer.Exit(1)


@app.command()
def db_info():
    """
    Show database connection and configuration information.
    """
    from .database import get_database_info, check_database_connection

    config = get_config()

    try:
        typer.echo("Database Information:")
        typer.echo("=" * 50)

        db_info = get_database_info()

        if 'error' in db_info:
            typer.echo(f"❌ Error getting database info: {db_info['error']}", err=True)
            raise typer.Exit(1)

        typer.echo(f"Database URL: {db_info.get('database_url', 'Not configured')}")
        typer.echo(f"Driver: {db_info.get('driver', 'Unknown')}")
        typer.echo(f"Connected: {'✅ Yes' if db_info.get('connected') else '❌ No'}")

        # SQLite-specific information
        if 'database_file' in db_info:
            typer.echo(f"Database file: {db_info['database_file']}")
            typer.echo(f"File exists: {'✅ Yes' if db_info.get('file_exists') else '❌ No'}")
            if db_info.get('file_size') is not None:
                size_mb = db_info['file_size'] / (1024 * 1024)
                typer.echo(f"File size: {size_mb:.2f} MB")

        if config.debug:
            logger.info("Database info command completed")

    except Exception as e:
        typer.echo(f"❌ Error retrieving database information: {e}", err=True)
        if config.debug:
            logger.exception("Error retrieving database information")
        raise typer.Exit(1)


@app.command()
def import_recipes(
    file_path: str = typer.Argument(..., help="Path to JSON file containing recipes"),
    skip_duplicates: bool = typer.Option(
        True,
        "--skip-duplicates/--allow-duplicates",
        help="Skip duplicate recipes during import"
    )
):
    """
    Import recipes from a JSON file.

    The JSON file should contain either a single recipe object or an array of recipe objects.
    Required fields: title
    Optional fields: description, prep_time, cook_time, servings, cuisine, dietary_tags, etc.
    """
    from .recipe_import import RecipeImporter, RecipeImportError

    config = get_config()

    try:
        typer.echo(f"Importing recipes from: {file_path}")

        importer = RecipeImporter()
        imported, skipped, errors = importer.import_from_json(file_path, skip_duplicates)

        # Report results
        typer.echo(f"✅ Import completed!")
        typer.echo(f"  Imported: {imported} recipes")
        if skipped > 0:
            typer.echo(f"  Skipped: {skipped} duplicates")

        if errors:
            typer.echo(f"  Errors: {len(errors)}")
            for error in errors:
                typer.echo(f"    - {error}", err=True)

        if config.debug:
            logger.info(f"Recipe import completed: {imported} imported, {skipped} skipped, {len(errors)} errors")

    except RecipeImportError as e:
        typer.echo(f"❌ Import failed: {e}", err=True)
        if config.debug:
            logger.error(f"Recipe import failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error during import: {e}", err=True)
        if config.debug:
            logger.exception("Unexpected error during recipe import")
        raise typer.Exit(1)


@app.command()
def import_csv(
    file_path: str = typer.Argument(..., help="Path to CSV file containing recipes"),
    skip_duplicates: bool = typer.Option(
        True,
        "--skip-duplicates/--allow-duplicates",
        help="Skip duplicate recipes during import"
    )
):
    """
    Import recipes from a CSV file.

    The CSV file should have a header row with column names matching recipe fields.
    Required columns: title
    Optional columns: description, prep_time, cook_time, servings, cuisine, dietary_tags, etc.
    """
    from .recipe_import import RecipeImporter, RecipeImportError

    config = get_config()

    try:
        typer.echo(f"Importing recipes from CSV: {file_path}")

        importer = RecipeImporter()
        imported, skipped, errors = importer.import_from_csv(file_path, skip_duplicates)

        # Report results
        typer.echo(f"✅ Import completed!")
        typer.echo(f"  Imported: {imported} recipes")
        if skipped > 0:
            typer.echo(f"  Skipped: {skipped} duplicates")

        if errors:
            typer.echo(f"  Errors: {len(errors)}")
            for error in errors:
                typer.echo(f"    - {error}", err=True)

        if config.debug:
            logger.info(f"CSV import completed: {imported} imported, {skipped} skipped, {len(errors)} errors")

    except RecipeImportError as e:
        typer.echo(f"❌ Import failed: {e}", err=True)
        if config.debug:
            logger.error(f"CSV import failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error during import: {e}", err=True)
        if config.debug:
            logger.exception("Unexpected error during CSV import")
        raise typer.Exit(1)


@app.command()
def import_url(
    url: str = typer.Argument(..., help="URL to fetch recipe JSON from"),
    skip_duplicates: bool = typer.Option(
        True,
        "--skip-duplicates/--allow-duplicates",
        help="Skip duplicate recipes during import"
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Request timeout in seconds"
    )
):
    """
    Import recipes from a URL that returns JSON data.

    The URL should return either a single recipe object or an array of recipe objects in JSON format.
    """
    from .recipe_import import RecipeImporter, RecipeImportError

    config = get_config()

    try:
        typer.echo(f"Importing recipes from URL: {url}")

        importer = RecipeImporter()
        imported, skipped, errors = importer.import_from_url(url, skip_duplicates, timeout)

        # Report results
        typer.echo(f"✅ Import completed!")
        typer.echo(f"  Imported: {imported} recipes")
        if skipped > 0:
            typer.echo(f"  Skipped: {skipped} duplicates")

        if errors:
            typer.echo(f"  Errors: {len(errors)}")
            for error in errors:
                typer.echo(f"    - {error}", err=True)

        if config.debug:
            logger.info(f"URL import completed: {imported} imported, {skipped} skipped, {len(errors)} errors")

    except RecipeImportError as e:
        typer.echo(f"❌ Import failed: {e}", err=True)
        if config.debug:
            logger.error(f"URL import failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error during import: {e}", err=True)
        if config.debug:
            logger.exception("Unexpected error during URL import")
        raise typer.Exit(1)


@app.command()
def list_recipes(
    page: int = typer.Option(1, "--page", help="Page number"),
    per_page: int = typer.Option(10, "--per-page", help="Recipes per page"),
    cuisine: Optional[str] = typer.Option(None, "--cuisine", help="Filter by cuisine"),
    max_time: Optional[int] = typer.Option(None, "--max-time", help="Maximum total time in minutes"),
    diet: Optional[str] = typer.Option(None, "--diet", help="Filter by dietary tag"),
    search: Optional[str] = typer.Option(None, "--search", help="Search in title and description"),
    sort_by: str = typer.Option("title", "--sort-by", help="Sort by field (title, prep_time, created_at)"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed recipe information")
):
    """
    List recipes with filtering, pagination, and sorting options.
    """
    from .recipe_management import RecipeManager, RecipeFormatter

    config = get_config()

    try:
        recipes, total_count, total_pages = RecipeManager.list_recipes(
            page=page,
            per_page=per_page,
            cuisine=cuisine,
            max_time=max_time,
            diet=diet,
            search=search,
            sort_by=sort_by
        )

        if not recipes:
            typer.echo("No recipes found.")
            return

        # Display header
        typer.echo(f"Recipes (Page {page} of {total_pages}, {total_count} total)")
        typer.echo("=" * 60)

        # Display recipes
        for recipe in recipes:
            if detailed:
                typer.echo(RecipeFormatter.format_recipe_details(recipe))
                typer.echo("-" * 40)
            else:
                typer.echo(RecipeFormatter.format_recipe_summary(recipe))

        # Display pagination info
        if total_pages > 1:
            typer.echo(f"\nPage {page} of {total_pages}")
            if page < total_pages:
                typer.echo(f"Use --page {page + 1} to see more recipes")

        if config.debug:
            logger.info(f"Listed {len(recipes)} recipes (page {page}/{total_pages})")

    except Exception as e:
        typer.echo(f"❌ Error listing recipes: {e}", err=True)
        if config.debug:
            logger.exception("Error listing recipes")
        raise typer.Exit(1)


@app.command()
def update_recipe(
    recipe_id: int = typer.Argument(..., help="Recipe ID to update")
):
    """
    Interactively update a recipe's fields.

    This command will prompt you to update various fields of the recipe.
    Press Enter to keep the current value, or type a new value to change it.
    """
    from .recipe_management import RecipeManager, RecipeFormatter

    config = get_config()

    try:
        # Get the recipe
        recipe = RecipeManager.get_recipe_by_id(recipe_id)
        if not recipe:
            typer.echo(f"❌ Recipe with ID {recipe_id} not found.", err=True)
            raise typer.Exit(1)

        typer.echo("Current recipe:")
        typer.echo(RecipeFormatter.format_recipe_details(recipe))
        typer.echo("\nUpdate recipe (press Enter to keep current value):")

        updates = {}

        # Title
        new_title = typer.prompt(f"Title", default=recipe.title)
        if new_title != recipe.title:
            updates['title'] = new_title

        # Description
        current_desc = recipe.description or ""
        new_desc = typer.prompt(f"Description", default=current_desc)
        if new_desc != current_desc:
            updates['description'] = new_desc if new_desc else None

        # Cuisine
        current_cuisine = recipe.cuisine or ""
        new_cuisine = typer.prompt(f"Cuisine", default=current_cuisine)
        if new_cuisine != current_cuisine:
            updates['cuisine'] = new_cuisine if new_cuisine else None

        # Prep time
        current_prep = str(recipe.prep_time) if recipe.prep_time else ""
        new_prep = typer.prompt(f"Prep time (minutes)", default=current_prep)
        if new_prep != current_prep:
            try:
                updates['prep_time'] = int(new_prep) if new_prep else None
            except ValueError:
                typer.echo("Invalid prep time, keeping current value")

        # Cook time
        current_cook = str(recipe.cook_time) if recipe.cook_time else ""
        new_cook = typer.prompt(f"Cook time (minutes)", default=current_cook)
        if new_cook != current_cook:
            try:
                updates['cook_time'] = int(new_cook) if new_cook else None
            except ValueError:
                typer.echo("Invalid cook time, keeping current value")

        # Servings
        current_servings = str(recipe.servings) if recipe.servings else ""
        new_servings = typer.prompt(f"Servings", default=current_servings)
        if new_servings != current_servings:
            try:
                updates['servings'] = int(new_servings) if new_servings else None
            except ValueError:
                typer.echo("Invalid servings, keeping current value")

        if not updates:
            typer.echo("No changes made.")
            return

        # Apply updates
        updated_recipe = RecipeManager.update_recipe(recipe_id, updates)
        if updated_recipe:
            typer.echo("✅ Recipe updated successfully!")
            typer.echo(RecipeFormatter.format_recipe_details(updated_recipe))
        else:
            typer.echo("❌ Failed to update recipe.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Updated recipe {recipe_id}: {list(updates.keys())}")

    except Exception as e:
        typer.echo(f"❌ Error updating recipe: {e}", err=True)
        if config.debug:
            logger.exception("Error updating recipe")
        raise typer.Exit(1)


@app.command()
def delete_recipe(
    recipe_id: int = typer.Argument(..., help="Recipe ID to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")
):
    """
    Delete a recipe and its associated meal plans.

    This will permanently delete the recipe and remove it from any meal plans.
    Use --force to skip the confirmation prompt.
    """
    from .recipe_management import RecipeManager, RecipeFormatter

    config = get_config()

    try:
        # Get the recipe
        recipe = RecipeManager.get_recipe_by_id(recipe_id)
        if not recipe:
            typer.echo(f"❌ Recipe with ID {recipe_id} not found.", err=True)
            raise typer.Exit(1)

        # Show recipe details
        typer.echo("Recipe to delete:")
        typer.echo(RecipeFormatter.format_recipe_details(recipe))

        # Confirmation
        if not force:
            confirm = typer.confirm(
                f"\nAre you sure you want to delete '{recipe.title}'? "
                "This will also remove it from any meal plans."
            )
            if not confirm:
                typer.echo("Deletion cancelled.")
                return

        # Delete the recipe
        success = RecipeManager.delete_recipe(recipe_id)
        if success:
            typer.echo(f"✅ Recipe '{recipe.title}' deleted successfully!")
        else:
            typer.echo("❌ Failed to delete recipe.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Deleted recipe {recipe_id}: {recipe.title}")

    except Exception as e:
        typer.echo(f"❌ Error deleting recipe: {e}", err=True)
        if config.debug:
            logger.exception("Error deleting recipe")
        raise typer.Exit(1)


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
