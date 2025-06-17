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


@app.command()
def search_ingredients(
    search_term: Optional[str] = typer.Option(None, "--search", help="Search term for ingredient names"),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category"),
    min_calories: Optional[float] = typer.Option(None, "--min-calories", help="Minimum calories per 100g"),
    max_calories: Optional[float] = typer.Option(None, "--max-calories", help="Maximum calories per 100g"),
    min_protein: Optional[float] = typer.Option(None, "--min-protein", help="Minimum protein per 100g"),
    max_protein: Optional[float] = typer.Option(None, "--max-protein", help="Maximum protein per 100g"),
    min_carbs: Optional[float] = typer.Option(None, "--min-carbs", help="Minimum carbs per 100g"),
    max_carbs: Optional[float] = typer.Option(None, "--max-carbs", help="Maximum carbs per 100g"),
    min_fat: Optional[float] = typer.Option(None, "--min-fat", help="Minimum fat per 100g"),
    max_fat: Optional[float] = typer.Option(None, "--max-fat", help="Maximum fat per 100g"),
    min_fiber: Optional[float] = typer.Option(None, "--min-fiber", help="Minimum fiber per 100g"),
    max_fiber: Optional[float] = typer.Option(None, "--max-fiber", help="Maximum fiber per 100g"),
    sort_by: str = typer.Option("name", "--sort-by", help="Sort by field (name, category, calories_per_100g, protein_per_100g)"),
    sort_order: str = typer.Option("asc", "--sort-order", help="Sort order (asc, desc)"),
    page: int = typer.Option(1, "--page", help="Page number"),
    per_page: int = typer.Option(20, "--per-page", help="Ingredients per page"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed ingredient information")
):
    """
    Search ingredients with advanced filtering options.

    Filter ingredients by nutritional content, category, and other criteria.
    Supports pagination and sorting for large result sets.
    """
    from .ingredient_search import IngredientSearchCriteria, IngredientSearcher
    from .ingredient_management import IngredientFormatter

    config = get_config()

    try:
        # Create search criteria
        criteria = IngredientSearchCriteria(
            search_term=search_term,
            category=category,
            min_calories=min_calories,
            max_calories=max_calories,
            min_protein=min_protein,
            max_protein=max_protein,
            min_carbs=min_carbs,
            max_carbs=max_carbs,
            min_fat=min_fat,
            max_fat=max_fat,
            min_fiber=min_fiber,
            max_fiber=max_fiber,
            sort_by=sort_by,
            sort_order=sort_order
        )

        ingredients, total_count, total_pages = IngredientSearcher.search_ingredients(
            criteria, page=page, per_page=per_page
        )

        if not ingredients:
            typer.echo("No ingredients found matching the criteria.")
            return

        # Display header
        typer.echo(f"Ingredients (Page {page} of {total_pages}, {total_count} total)")
        typer.echo("=" * 70)

        # Display ingredients
        for ingredient in ingredients:
            if detailed:
                typer.echo(IngredientFormatter.format_ingredient_details(ingredient))
                typer.echo("-" * 50)
            else:
                typer.echo(IngredientFormatter.format_ingredient_summary(ingredient))

        # Display pagination info
        if total_pages > 1:
            typer.echo(f"\nPage {page} of {total_pages}")
            if page < total_pages:
                typer.echo(f"Use --page {page + 1} to see more ingredients")

        if config.debug:
            logger.info(f"Found {len(ingredients)} ingredients (page {page}/{total_pages})")

    except Exception as e:
        typer.echo(f"❌ Error searching ingredients: {e}", err=True)
        if config.debug:
            logger.exception("Error searching ingredients")
        raise typer.Exit(1)


@app.command()
def list_ingredients(
    page: int = typer.Option(1, "--page", help="Page number"),
    per_page: int = typer.Option(20, "--per-page", help="Ingredients per page"),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category"),
    search: Optional[str] = typer.Option(None, "--search", help="Search in ingredient names"),
    sort_by: str = typer.Option("name", "--sort-by", help="Sort by field (name, category, calories_per_100g, protein_per_100g)"),
    sort_order: str = typer.Option("asc", "--sort-order", help="Sort order (asc, desc)"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed ingredient information")
):
    """
    List ingredients with filtering, pagination, and sorting options.
    """
    from .ingredient_management import IngredientManager, IngredientFormatter

    config = get_config()

    try:
        ingredients, total_count, total_pages = IngredientManager.list_ingredients(
            page=page,
            per_page=per_page,
            category=category,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if not ingredients:
            typer.echo("No ingredients found.")
            return

        # Display header
        typer.echo(f"Ingredients (Page {page} of {total_pages}, {total_count} total)")
        typer.echo("=" * 70)

        # Display ingredients
        for ingredient in ingredients:
            if detailed:
                typer.echo(IngredientFormatter.format_ingredient_details(ingredient))
                typer.echo("-" * 50)
            else:
                typer.echo(IngredientFormatter.format_ingredient_summary(ingredient))

        # Display pagination info
        if total_pages > 1:
            typer.echo(f"\nPage {page} of {total_pages}")
            if page < total_pages:
                typer.echo(f"Use --page {page + 1} to see more ingredients")

        if config.debug:
            logger.info(f"Listed {len(ingredients)} ingredients (page {page}/{total_pages})")

    except Exception as e:
        typer.echo(f"❌ Error listing ingredients: {e}", err=True)
        if config.debug:
            logger.exception("Error listing ingredients")
        raise typer.Exit(1)


@app.command()
def add_ingredient(
    name: str = typer.Argument(..., help="Ingredient name"),
    category: Optional[str] = typer.Option(None, "--category", help="Ingredient category"),
    calories: Optional[float] = typer.Option(None, "--calories", help="Calories per 100g"),
    protein: Optional[float] = typer.Option(None, "--protein", help="Protein per 100g"),
    carbs: Optional[float] = typer.Option(None, "--carbs", help="Carbohydrates per 100g"),
    fat: Optional[float] = typer.Option(None, "--fat", help="Fat per 100g"),
    fiber: Optional[float] = typer.Option(None, "--fiber", help="Fiber per 100g"),
    sugar: Optional[float] = typer.Option(None, "--sugar", help="Sugar per 100g"),
    sodium: Optional[float] = typer.Option(None, "--sodium", help="Sodium per 100g (mg)"),
    unit: Optional[str] = typer.Option(None, "--unit", help="Common unit (e.g., cup, tbsp)"),
    unit_weight: Optional[float] = typer.Option(None, "--unit-weight", help="Weight of one unit in grams")
):
    """
    Add a new ingredient to the database.

    Specify nutritional information per 100g and optional unit conversions.
    """
    from .ingredient_management import IngredientManager, IngredientFormatter

    config = get_config()

    try:
        # Check if ingredient already exists
        existing = IngredientManager.get_ingredient_by_name(name)
        if existing:
            typer.echo(f"❌ Ingredient '{name}' already exists with ID {existing.id}", err=True)
            raise typer.Exit(1)

        # Create the ingredient
        ingredient = IngredientManager.create_ingredient(
            name=name,
            category=category,
            calories_per_100g=calories,
            protein_per_100g=protein,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
            fiber_per_100g=fiber,
            sugar_per_100g=sugar,
            sodium_per_100g=sodium,
            common_unit=unit,
            unit_weight_grams=unit_weight
        )

        typer.echo("✅ Ingredient added successfully!")
        typer.echo(IngredientFormatter.format_ingredient_details(ingredient))

        if config.debug:
            logger.info(f"Added ingredient: {ingredient.name} (ID: {ingredient.id})")

    except Exception as e:
        typer.echo(f"❌ Error adding ingredient: {e}", err=True)
        if config.debug:
            logger.exception("Error adding ingredient")
        raise typer.Exit(1)


@app.command()
def update_ingredient(
    ingredient_id: int = typer.Argument(..., help="Ingredient ID to update")
):
    """
    Interactively update an ingredient's fields.

    This command will prompt you to update various fields of the ingredient.
    Press Enter to keep the current value, or type a new value to change it.
    """
    from .ingredient_management import IngredientManager, IngredientFormatter

    config = get_config()

    try:
        # Get the ingredient
        ingredient = IngredientManager.get_ingredient_by_id(ingredient_id)
        if not ingredient:
            typer.echo(f"❌ Ingredient with ID {ingredient_id} not found.", err=True)
            raise typer.Exit(1)

        typer.echo("Current ingredient:")
        typer.echo(IngredientFormatter.format_ingredient_details(ingredient))
        typer.echo("\nUpdate ingredient (press Enter to keep current value):")

        updates = {}

        # Name
        new_name = typer.prompt(f"Name", default=ingredient.name)
        if new_name != ingredient.name:
            updates['name'] = new_name

        # Category
        current_category = ingredient.category or ""
        new_category = typer.prompt(f"Category", default=current_category)
        if new_category != current_category:
            updates['category'] = new_category if new_category else None

        # Nutritional fields
        nutrition_fields = [
            ('calories_per_100g', 'Calories per 100g'),
            ('protein_per_100g', 'Protein per 100g'),
            ('carbs_per_100g', 'Carbs per 100g'),
            ('fat_per_100g', 'Fat per 100g'),
            ('fiber_per_100g', 'Fiber per 100g'),
            ('sugar_per_100g', 'Sugar per 100g'),
            ('sodium_per_100g', 'Sodium per 100g (mg)')
        ]

        for field, prompt_text in nutrition_fields:
            current_value = str(getattr(ingredient, field)) if getattr(ingredient, field) else ""
            new_value = typer.prompt(prompt_text, default=current_value)
            if new_value != current_value:
                try:
                    updates[field] = float(new_value) if new_value else None
                except ValueError:
                    typer.echo(f"Invalid value for {prompt_text}, keeping current value")

        # Common unit
        current_unit = ingredient.common_unit or ""
        new_unit = typer.prompt(f"Common unit", default=current_unit)
        if new_unit != current_unit:
            updates['common_unit'] = new_unit if new_unit else None

        # Unit weight
        current_weight = str(ingredient.unit_weight_grams) if ingredient.unit_weight_grams else ""
        new_weight = typer.prompt(f"Unit weight (grams)", default=current_weight)
        if new_weight != current_weight:
            try:
                updates['unit_weight_grams'] = float(new_weight) if new_weight else None
            except ValueError:
                typer.echo("Invalid unit weight, keeping current value")

        if not updates:
            typer.echo("No changes made.")
            return

        # Apply updates
        updated_ingredient = IngredientManager.update_ingredient(ingredient_id, updates)
        if updated_ingredient:
            typer.echo("✅ Ingredient updated successfully!")
            typer.echo(IngredientFormatter.format_ingredient_details(updated_ingredient))
        else:
            typer.echo("❌ Failed to update ingredient.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Updated ingredient {ingredient_id}: {list(updates.keys())}")

    except Exception as e:
        typer.echo(f"❌ Error updating ingredient: {e}", err=True)
        if config.debug:
            logger.exception("Error updating ingredient")
        raise typer.Exit(1)


@app.command()
def delete_ingredient(
    ingredient_id: int = typer.Argument(..., help="Ingredient ID to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")
):
    """
    Delete an ingredient and its recipe associations.

    This will permanently delete the ingredient and remove it from any recipes.
    Use --force to skip the confirmation prompt.
    """
    from .ingredient_management import IngredientManager, IngredientFormatter

    config = get_config()

    try:
        # Get the ingredient
        ingredient = IngredientManager.get_ingredient_by_id(ingredient_id)
        if not ingredient:
            typer.echo(f"❌ Ingredient with ID {ingredient_id} not found.", err=True)
            raise typer.Exit(1)

        # Show ingredient details
        typer.echo("Ingredient to delete:")
        typer.echo(IngredientFormatter.format_ingredient_details(ingredient))

        # Confirmation
        if not force:
            confirm = typer.confirm(
                f"\nAre you sure you want to delete '{ingredient.name}'? "
                "This will also remove it from any recipes."
            )
            if not confirm:
                typer.echo("Deletion cancelled.")
                return

        # Delete the ingredient
        success = IngredientManager.delete_ingredient(ingredient_id)
        if success:
            typer.echo(f"✅ Ingredient '{ingredient.name}' deleted successfully!")
        else:
            typer.echo("❌ Failed to delete ingredient.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Deleted ingredient {ingredient_id}: {ingredient.name}")

    except Exception as e:
        typer.echo(f"❌ Error deleting ingredient: {e}", err=True)
        if config.debug:
            logger.exception("Error deleting ingredient")
        raise typer.Exit(1)


@app.command()
def ingredient_stats():
    """
    Show ingredient database statistics and analytics.

    Displays information about ingredient categories, nutritional averages,
    and most frequently used ingredients.
    """
    from .ingredient_management import IngredientManager
    from .ingredient_search import IngredientSearcher

    config = get_config()

    try:
        stats = IngredientManager.get_ingredient_statistics()

        typer.echo("📊 Ingredient Database Statistics")
        typer.echo("=" * 50)

        # Basic counts
        typer.echo(f"Total ingredients: {stats['total_ingredients']}")

        # Categories
        if stats['categories']:
            typer.echo(f"\nIngredients by category:")
            for category, count in sorted(stats['categories'].items()):
                typer.echo(f"  {category}: {count}")

        # Nutritional averages
        typer.echo(f"\nNutritional averages (per 100g):")
        if stats['avg_calories_per_100g']:
            typer.echo(f"  Average calories: {stats['avg_calories_per_100g']}")
        if stats['avg_protein_per_100g']:
            typer.echo(f"  Average protein: {stats['avg_protein_per_100g']}g")

        # Most used ingredients
        if stats['most_used']:
            typer.echo(f"\nMost used ingredients in recipes:")
            for name, count in stats['most_used']:
                typer.echo(f"  {name}: used in {count} recipe(s)")

        # Quick nutrition searches
        typer.echo(f"\nQuick nutrition insights:")

        # High protein ingredients
        high_protein = IngredientSearcher.find_high_protein_ingredients(min_protein=15)
        typer.echo(f"  High protein ingredients (≥15g): {len(high_protein)}")

        # Low calorie ingredients
        low_calorie = IngredientSearcher.find_low_calorie_ingredients(max_calories=50)
        typer.echo(f"  Low calorie ingredients (≤50 cal): {len(low_calorie)}")

        # High fiber ingredients
        high_fiber = IngredientSearcher.find_high_fiber_ingredients(min_fiber=5)
        typer.echo(f"  High fiber ingredients (≥5g): {len(high_fiber)}")

        # Categories
        categories = IngredientSearcher.get_ingredient_categories()
        typer.echo(f"  Available categories: {len(categories)}")

        if config.debug:
            logger.info("Generated ingredient statistics")

    except Exception as e:
        typer.echo(f"❌ Error generating ingredient statistics: {e}", err=True)
        if config.debug:
            logger.exception("Error generating ingredient statistics")
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
