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


@app.command()
def schedule_meal(
    recipe_id: int = typer.Argument(..., help="Recipe ID to schedule"),
    target_date: str = typer.Argument(..., help="Date to schedule (YYYY-MM-DD)"),
    meal_type: str = typer.Argument(..., help="Meal type (breakfast, lunch, dinner, snack)"),
    servings: int = typer.Option(1, "--servings", help="Number of servings"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes for the meal"),
    allow_conflicts: bool = typer.Option(False, "--allow-conflicts", help="Allow multiple meals of same type on same date")
):
    """
    Schedule a meal for a specific date and meal type.

    Schedule a recipe for breakfast, lunch, dinner, or snack on a specific date.
    By default, conflicts (multiple meals of same type on same date) are not allowed.
    """
    from datetime import datetime
    from .meal_planning import MealPlanner, MealPlanningError
    from .models import MealType

    config = get_config()

    try:
        # Parse date
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(f"❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-15)", err=True)
            raise typer.Exit(1)

        # Parse meal type
        try:
            parsed_meal_type = MealType(meal_type.lower())
        except ValueError:
            valid_types = [mt.value for mt in MealType]
            typer.echo(f"❌ Invalid meal type. Valid options: {', '.join(valid_types)}", err=True)
            raise typer.Exit(1)

        # Schedule the meal
        plan = MealPlanner.schedule_meal(
            target_date=parsed_date,
            meal_type=parsed_meal_type,
            recipe_id=recipe_id,
            servings=servings,
            notes=notes,
            allow_conflicts=allow_conflicts
        )

        typer.echo("✅ Meal scheduled successfully!")
        typer.echo(f"Plan ID: {plan.id}")
        typer.echo(f"Date: {plan.date}")
        typer.echo(f"Meal Type: {plan.meal_type.value.title()}")
        typer.echo(f"Recipe ID: {plan.recipe_id}")
        typer.echo(f"Servings: {plan.servings}")
        if plan.notes:
            typer.echo(f"Notes: {plan.notes}")

        if config.debug:
            logger.info(f"Scheduled meal plan {plan.id} for {parsed_date}")

    except MealPlanningError as e:
        typer.echo(f"❌ Scheduling failed: {e}", err=True)
        if config.debug:
            logger.error(f"Meal scheduling failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error scheduling meal: {e}", err=True)
        if config.debug:
            logger.exception("Error scheduling meal")
        raise typer.Exit(1)


@app.command()
def view_calendar(
    target_date: Optional[str] = typer.Option(None, "--date", help="Date for calendar view (YYYY-MM-DD), defaults to today"),
    view_type: str = typer.Option("week", "--view", help="Calendar view type (week, month)"),
    include_recipes: bool = typer.Option(False, "--detailed", help="Include recipe details"),
    start_monday: bool = typer.Option(True, "--start-monday/--start-sunday", help="Week starts on Monday or Sunday")
):
    """
    Display a calendar view of scheduled meals.

    Show weekly or monthly calendar with meal plans. Use --detailed to include
    recipe information in the calendar view.
    """
    from datetime import datetime, date
    from .calendar_management import CalendarManager

    config = get_config()

    try:
        # Parse target date
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-15)", err=True)
                raise typer.Exit(1)
        else:
            parsed_date = date.today()

        if view_type.lower() == "week":
            calendar_data = CalendarManager.get_weekly_calendar(
                target_date=parsed_date,
                start_on_monday=start_monday,
                include_recipes=include_recipes
            )

            # Display weekly calendar
            typer.echo(f"📅 Weekly Calendar - Week {calendar_data['week_number']}")
            typer.echo(f"Week of {calendar_data['start_date']} to {calendar_data['end_date']}")
            typer.echo("=" * 70)

            for day in calendar_data['days']:
                day_header = f"{day['day_name']} {day['date']}"
                if day['is_today']:
                    day_header += " (Today)"
                if day['is_weekend']:
                    day_header += " 🌅"

                typer.echo(f"\n{day_header}")
                typer.echo("-" * len(day_header))

                if day['total_meals'] == 0:
                    typer.echo("  No meals scheduled")
                else:
                    for meal_type, meals in day['meals'].items():
                        if meals:
                            typer.echo(f"  {meal_type.title()}:")
                            for meal in meals:
                                status = "✅" if meal['completed'] else "⏳"
                                meal_info = f"    {status} Recipe ID {meal['recipe_id']}"
                                if meal['servings'] > 1:
                                    meal_info += f" ({meal['servings']} servings)"

                                if include_recipes and 'recipe' in meal:
                                    recipe = meal['recipe']
                                    meal_info += f" - {recipe['title']}"
                                    if recipe['cuisine']:
                                        meal_info += f" ({recipe['cuisine']})"

                                typer.echo(meal_info)

                                if meal['notes']:
                                    typer.echo(f"      Note: {meal['notes']}")

                    completion_info = f"  📊 {day['completed_meals']}/{day['total_meals']} meals completed"
                    typer.echo(completion_info)

        elif view_type.lower() == "month":
            calendar_data = CalendarManager.get_monthly_calendar(
                year=parsed_date.year,
                month=parsed_date.month,
                include_recipes=include_recipes
            )

            # Display monthly calendar
            typer.echo(f"📅 Monthly Calendar - {calendar_data['month_name']} {calendar_data['year']}")
            typer.echo("=" * 70)

            # Group days by week for better display
            weeks = []
            current_week = []

            for day in calendar_data['days']:
                current_week.append(day)
                if len(current_week) == 7 or day['date'] == calendar_data['end_date']:
                    weeks.append(current_week)
                    current_week = []

            for week_num, week in enumerate(weeks, 1):
                typer.echo(f"\nWeek {week_num}:")
                for day in week:
                    day_info = f"  {day['day']:2d} {day['date'].strftime('%a')}"
                    if day['is_today']:
                        day_info += " (Today)"

                    if day['total_meals'] > 0:
                        day_info += f" - {day['total_meals']} meals"
                        if day['completed_meals'] > 0:
                            day_info += f" ({day['completed_meals']} done)"

                    typer.echo(day_info)

        else:
            typer.echo(f"❌ Invalid view type. Use 'week' or 'month'", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Displayed {view_type} calendar for {parsed_date}")

    except Exception as e:
        typer.echo(f"❌ Error displaying calendar: {e}", err=True)
        if config.debug:
            logger.exception("Error displaying calendar")
        raise typer.Exit(1)


@app.command()
def list_plans(
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD), defaults to today"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD), defaults to start date"),
    meal_type: Optional[str] = typer.Option(None, "--meal-type", help="Filter by meal type"),
    completed: Optional[bool] = typer.Option(None, "--completed", help="Filter by completion status"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed plan information")
):
    """
    List meal plans with filtering options.

    Display meal plans for a date range with optional filtering by meal type
    and completion status.
    """
    from datetime import datetime, date
    from .meal_planning import MealPlanner
    from .models import MealType

    config = get_config()

    try:
        # Parse dates
        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid start date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_start = date.today()

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid end date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_end = parsed_start

        # Parse meal type filter
        parsed_meal_type = None
        if meal_type:
            try:
                parsed_meal_type = MealType(meal_type.lower())
            except ValueError:
                valid_types = [mt.value for mt in MealType]
                typer.echo(f"❌ Invalid meal type. Valid options: {', '.join(valid_types)}", err=True)
                raise typer.Exit(1)

        # Get plans
        plans = MealPlanner.get_plans_for_date_range(parsed_start, parsed_end)

        # Apply filters
        if parsed_meal_type:
            plans = [p for p in plans if p.meal_type == parsed_meal_type]

        if completed is not None:
            plans = [p for p in plans if p.completed == completed]

        if not plans:
            typer.echo("No meal plans found matching the criteria.")
            return

        # Display header
        date_range = f"{parsed_start}" if parsed_start == parsed_end else f"{parsed_start} to {parsed_end}"
        typer.echo(f"Meal Plans ({date_range}) - {len(plans)} found")
        typer.echo("=" * 70)

        # Get recipe details for display
        recipe_cache = {}
        if plans:
            from .database import get_db_session
            from .models import Recipe

            with get_db_session() as session:
                recipe_ids = list(set(plan.recipe_id for plan in plans))
                recipes = session.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
                # Create a cache with recipe data, not objects
                for recipe in recipes:
                    recipe_cache[recipe.id] = {
                        'title': recipe.title,
                        'cuisine': recipe.cuisine,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time
                    }

        # Display plans
        for plan in plans:
            status = "✅" if plan.completed else "⏳"
            recipe_title = "Unknown Recipe"

            if plan.recipe_id in recipe_cache:
                recipe_title = recipe_cache[plan.recipe_id]['title']

            plan_info = f"{status} [{plan.id}] {plan.date} - {plan.meal_type.value.title()}: {recipe_title}"
            if plan.servings > 1:
                plan_info += f" ({plan.servings} servings)"

            typer.echo(plan_info)

            if detailed:
                if plan.notes:
                    typer.echo(f"    Notes: {plan.notes}")

                if plan.recipe_id in recipe_cache:
                    recipe_data = recipe_cache[plan.recipe_id]
                    if recipe_data['cuisine']:
                        typer.echo(f"    Cuisine: {recipe_data['cuisine']}")
                    if recipe_data['prep_time'] or recipe_data['cook_time']:
                        time_info = []
                        if recipe_data['prep_time']:
                            time_info.append(f"Prep: {recipe_data['prep_time']}min")
                        if recipe_data['cook_time']:
                            time_info.append(f"Cook: {recipe_data['cook_time']}min")
                        typer.echo(f"    Time: {', '.join(time_info)}")

                typer.echo(f"    Created: {plan.created_at.strftime('%Y-%m-%d %H:%M')}")
                typer.echo("")

        # Summary
        completed_count = sum(1 for p in plans if p.completed)
        completion_rate = (completed_count / len(plans) * 100) if plans else 0
        typer.echo(f"\n📊 Summary: {completed_count}/{len(plans)} completed ({completion_rate:.1f}%)")

        if config.debug:
            logger.info(f"Listed {len(plans)} meal plans for {date_range}")

    except Exception as e:
        typer.echo(f"❌ Error listing meal plans: {e}", err=True)
        if config.debug:
            logger.exception("Error listing meal plans")
        raise typer.Exit(1)


@app.command()
def complete_meal(
    plan_id: int = typer.Argument(..., help="Meal plan ID to mark as completed"),
    uncomplete: bool = typer.Option(False, "--uncomplete", help="Mark as incomplete instead")
):
    """
    Mark a meal plan as completed or incomplete.

    Use this command to track which meals you've actually prepared and eaten.
    """
    from .meal_planning import MealPlanner

    config = get_config()

    try:
        # Update completion status
        plan = MealPlanner.complete_meal(plan_id, completed=not uncomplete)

        if not plan:
            typer.echo(f"❌ Meal plan with ID {plan_id} not found.", err=True)
            raise typer.Exit(1)

        status = "incomplete" if uncomplete else "completed"
        typer.echo(f"✅ Meal plan {plan_id} marked as {status}!")
        typer.echo(f"Date: {plan.date}")
        typer.echo(f"Meal Type: {plan.meal_type.value.title()}")
        typer.echo(f"Recipe ID: {plan.recipe_id}")

        if config.debug:
            logger.info(f"Marked meal plan {plan_id} as {status}")

    except Exception as e:
        typer.echo(f"❌ Error updating meal plan: {e}", err=True)
        if config.debug:
            logger.exception("Error updating meal plan completion")
        raise typer.Exit(1)


@app.command()
def update_plan(
    plan_id: int = typer.Argument(..., help="Meal plan ID to update")
):
    """
    Interactively update a meal plan's details.

    This command will prompt you to update various fields of the meal plan.
    Press Enter to keep the current value, or type a new value to change it.
    """
    from .meal_planning import MealPlanner
    from .models import MealType
    from datetime import datetime

    config = get_config()

    try:
        # Get the current plan
        plan = MealPlanner.get_meal_plan(plan_id)
        if not plan:
            typer.echo(f"❌ Meal plan with ID {plan_id} not found.", err=True)
            raise typer.Exit(1)

        typer.echo(f"Current meal plan details:")
        typer.echo(f"  Date: {plan.date}")
        typer.echo(f"  Meal Type: {plan.meal_type.value.title()}")
        typer.echo(f"  Recipe ID: {plan.recipe_id}")
        typer.echo(f"  Servings: {plan.servings}")
        typer.echo(f"  Notes: {plan.notes or 'None'}")
        typer.echo(f"  Completed: {'Yes' if plan.completed else 'No'}")
        typer.echo("\nUpdate meal plan (press Enter to keep current value):")

        updates = {}

        # Date
        new_date = typer.prompt(f"Date (YYYY-MM-DD)", default=str(plan.date))
        if new_date != str(plan.date):
            try:
                parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                updates['date'] = parsed_date
            except ValueError:
                typer.echo("Invalid date format, keeping current value")

        # Meal type
        current_meal_type = plan.meal_type.value
        valid_types = [mt.value for mt in MealType]
        new_meal_type = typer.prompt(f"Meal type ({', '.join(valid_types)})", default=current_meal_type)
        if new_meal_type != current_meal_type:
            if new_meal_type.lower() in valid_types:
                updates['meal_type'] = new_meal_type.lower()
            else:
                typer.echo("Invalid meal type, keeping current value")

        # Recipe ID
        new_recipe_id = typer.prompt(f"Recipe ID", default=str(plan.recipe_id))
        if new_recipe_id != str(plan.recipe_id):
            try:
                updates['recipe_id'] = int(new_recipe_id)
            except ValueError:
                typer.echo("Invalid recipe ID, keeping current value")

        # Servings
        new_servings = typer.prompt(f"Servings", default=str(plan.servings))
        if new_servings != str(plan.servings):
            try:
                updates['servings'] = int(new_servings)
            except ValueError:
                typer.echo("Invalid servings, keeping current value")

        # Notes
        current_notes = plan.notes or ""
        new_notes = typer.prompt(f"Notes", default=current_notes)
        if new_notes != current_notes:
            updates['notes'] = new_notes if new_notes else None

        # Completed
        current_completed = "yes" if plan.completed else "no"
        new_completed = typer.prompt(f"Completed (yes/no)", default=current_completed)
        if new_completed.lower() != current_completed:
            if new_completed.lower() in ['yes', 'y', 'true', '1']:
                updates['completed'] = True
            elif new_completed.lower() in ['no', 'n', 'false', '0']:
                updates['completed'] = False

        if not updates:
            typer.echo("No changes made.")
            return

        # Apply updates
        updated_plan = MealPlanner.update_meal_plan(plan_id, updates)
        if updated_plan:
            typer.echo("✅ Meal plan updated successfully!")
            typer.echo(f"Date: {updated_plan.date}")
            typer.echo(f"Meal Type: {updated_plan.meal_type.value.title()}")
            typer.echo(f"Recipe ID: {updated_plan.recipe_id}")
            typer.echo(f"Servings: {updated_plan.servings}")
            if updated_plan.notes:
                typer.echo(f"Notes: {updated_plan.notes}")
            typer.echo(f"Completed: {'Yes' if updated_plan.completed else 'No'}")
        else:
            typer.echo("❌ Failed to update meal plan.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Updated meal plan {plan_id}: {list(updates.keys())}")

    except Exception as e:
        typer.echo(f"❌ Error updating meal plan: {e}", err=True)
        if config.debug:
            logger.exception("Error updating meal plan")
        raise typer.Exit(1)


@app.command()
def delete_plan(
    plan_id: int = typer.Argument(..., help="Meal plan ID to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")
):
    """
    Delete a meal plan.

    Permanently remove a meal plan from the schedule.
    Use --force to skip the confirmation prompt.
    """
    from .meal_planning import MealPlanner

    config = get_config()

    try:
        # Get the plan for confirmation
        plan = MealPlanner.get_meal_plan(plan_id)
        if not plan:
            typer.echo(f"❌ Meal plan with ID {plan_id} not found.", err=True)
            raise typer.Exit(1)

        # Show plan details
        typer.echo("Meal plan to delete:")
        typer.echo(f"  ID: {plan.id}")
        typer.echo(f"  Date: {plan.date}")
        typer.echo(f"  Meal Type: {plan.meal_type.value.title()}")
        typer.echo(f"  Recipe ID: {plan.recipe_id}")

        # Confirmation
        if not force:
            confirm = typer.confirm(
                f"\nAre you sure you want to delete this meal plan?"
            )
            if not confirm:
                typer.echo("Deletion cancelled.")
                return

        # Delete the plan
        success = MealPlanner.delete_meal_plan(plan_id)
        if success:
            typer.echo(f"✅ Meal plan {plan_id} deleted successfully!")
        else:
            typer.echo("❌ Failed to delete meal plan.", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Deleted meal plan {plan_id}")

    except Exception as e:
        typer.echo(f"❌ Error deleting meal plan: {e}", err=True)
        if config.debug:
            logger.exception("Error deleting meal plan")
        raise typer.Exit(1)


@app.command()
def clear_schedule(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD), defaults to start date"),
    meal_type: Optional[str] = typer.Option(None, "--meal-type", help="Clear only specific meal type"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")
):
    """
    Clear meal plans for a date range.

    Remove all meal plans within the specified date range. Optionally filter
    by meal type to clear only specific types of meals.
    """
    from datetime import datetime
    from .meal_planning import MealPlanner
    from .models import MealType

    config = get_config()

    try:
        # Parse dates
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(f"❌ Invalid start date format. Use YYYY-MM-DD", err=True)
            raise typer.Exit(1)

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid end date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_end = None

        # Parse meal type filter
        parsed_meal_type = None
        if meal_type:
            try:
                parsed_meal_type = MealType(meal_type.lower())
            except ValueError:
                valid_types = [mt.value for mt in MealType]
                typer.echo(f"❌ Invalid meal type. Valid options: {', '.join(valid_types)}", err=True)
                raise typer.Exit(1)

        # Show what will be cleared
        date_range = f"{parsed_start}" if not parsed_end else f"{parsed_start} to {parsed_end}"
        meal_filter = f" ({parsed_meal_type.value} only)" if parsed_meal_type else ""

        typer.echo(f"This will clear meal plans for: {date_range}{meal_filter}")

        # Confirmation
        if not force:
            confirm = typer.confirm("Are you sure you want to clear these meal plans?")
            if not confirm:
                typer.echo("Clear operation cancelled.")
                return

        # Clear the schedule
        count = MealPlanner.clear_schedule(
            start_date=parsed_start,
            end_date=parsed_end,
            meal_type=parsed_meal_type
        )

        typer.echo(f"✅ Cleared {count} meal plan(s) successfully!")

        if config.debug:
            logger.info(f"Cleared {count} meal plans for {date_range}")

    except Exception as e:
        typer.echo(f"❌ Error clearing schedule: {e}", err=True)
        if config.debug:
            logger.exception("Error clearing schedule")
        raise typer.Exit(1)


@app.command()
def plan_stats(
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD), defaults to this week"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD), defaults to start date"),
    period: str = typer.Option("week", "--period", help="Predefined period (week, month, year)")
):
    """
    Show meal planning statistics and analytics.

    Display statistics about meal plans including completion rates, most planned
    recipes, and meal type distribution for a specified period.
    """
    from datetime import datetime, date, timedelta
    from .meal_planning import MealPlanner
    from .calendar_management import CalendarManager

    config = get_config()

    try:
        # Determine date range
        if start_date and end_date:
            # Use provided dates
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            # Use predefined period
            today = date.today()

            if period.lower() == "week":
                parsed_start, parsed_end = CalendarManager.get_week_dates(today)
            elif period.lower() == "month":
                parsed_start, parsed_end = CalendarManager.get_month_dates(today.year, today.month)
            elif period.lower() == "year":
                parsed_start = date(today.year, 1, 1)
                parsed_end = date(today.year, 12, 31)
            else:
                typer.echo(f"❌ Invalid period. Use 'week', 'month', or 'year'", err=True)
                raise typer.Exit(1)

        # Get statistics
        stats = MealPlanner.get_meal_plan_statistics(parsed_start, parsed_end)
        summary = CalendarManager.get_calendar_summary(parsed_start, parsed_end)

        # Display statistics
        typer.echo(f"📊 Meal Planning Statistics")
        typer.echo(f"Period: {parsed_start} to {parsed_end}")
        typer.echo("=" * 50)

        # Basic stats
        typer.echo(f"\n📅 Planning Overview:")
        typer.echo(f"  Total meal plans: {stats['total_plans']}")
        typer.echo(f"  Completed meals: {stats['completed_plans']}")
        typer.echo(f"  Completion rate: {stats['completion_rate']:.1f}%")
        typer.echo(f"  Days with meals: {summary['meal_statistics']['days_with_meals']}")
        typer.echo(f"  Average meals per day: {summary['meal_statistics']['avg_meals_per_day']}")

        # Meal type distribution
        typer.echo(f"\n🍽️ Meal Type Distribution:")
        for meal_type, count in stats['meal_type_counts'].items():
            percentage = (count / stats['total_plans'] * 100) if stats['total_plans'] > 0 else 0
            typer.echo(f"  {meal_type.title()}: {count} ({percentage:.1f}%)")

        # Most planned recipes
        if stats['most_planned_recipes']:
            typer.echo(f"\n🏆 Most Planned Recipes:")

            # Get recipe details
            from .database import get_db_session
            from .models import Recipe

            with get_db_session() as session:
                for recipe_id, count in stats['most_planned_recipes']:
                    recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
                    recipe_title = recipe.title if recipe else f"Recipe {recipe_id}"
                    typer.echo(f"  {recipe_title}: {count} times")

        # Recipe diversity
        typer.echo(f"\n🎯 Recipe Diversity:")
        typer.echo(f"  Unique recipes used: {summary['recipe_statistics']['unique_recipes']}")
        if stats['total_plans'] > 0:
            diversity_rate = (summary['recipe_statistics']['unique_recipes'] / stats['total_plans'] * 100)
            typer.echo(f"  Recipe diversity rate: {diversity_rate:.1f}%")

        if config.debug:
            logger.info(f"Generated meal planning statistics for {parsed_start} to {parsed_end}")

    except Exception as e:
        typer.echo(f"❌ Error generating statistics: {e}", err=True)
        if config.debug:
            logger.exception("Error generating meal planning statistics")
        raise typer.Exit(1)


@app.command()
def analyze_recipe(
    recipe_id: int = typer.Argument(..., help="Recipe ID to analyze"),
    servings: int = typer.Option(1, "--servings", help="Number of servings to analyze")
):
    """
    Analyze the nutritional content of a recipe.

    Display detailed nutritional information including calories, macronutrients,
    and micronutrients for the specified number of servings.
    """
    from .nutritional_analysis import NutritionalAnalyzer

    config = get_config()

    try:
        # Analyze the recipe
        nutrition = NutritionalAnalyzer.analyze_recipe(recipe_id, servings)

        if not nutrition:
            typer.echo(f"❌ Recipe with ID {recipe_id} not found.", err=True)
            raise typer.Exit(1)

        # Get recipe details for display
        from .database import get_db_session
        from .models import Recipe

        with get_db_session() as session:
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            recipe_title = recipe.title if recipe else f"Recipe {recipe_id}"

        # Display analysis
        typer.echo(f"🔬 Nutritional Analysis: {recipe_title}")
        if servings > 1:
            typer.echo(f"Servings: {servings}")
        typer.echo("=" * 50)

        # Macronutrients
        typer.echo(f"\n📊 Macronutrients:")
        typer.echo(f"  Calories: {nutrition.calories:.0f}")
        typer.echo(f"  Protein: {nutrition.protein:.1f}g")
        typer.echo(f"  Carbohydrates: {nutrition.carbs:.1f}g")
        typer.echo(f"  Fat: {nutrition.fat:.1f}g")

        # Micronutrients
        typer.echo(f"\n🌿 Micronutrients:")
        typer.echo(f"  Fiber: {nutrition.fiber:.1f}g")
        typer.echo(f"  Sugar: {nutrition.sugar:.1f}g")
        typer.echo(f"  Sodium: {nutrition.sodium:.0f}mg")

        # Macro ratios
        macro_ratios = NutritionalAnalyzer.calculate_macro_ratios(nutrition)
        typer.echo(f"\n⚖️ Macro Ratios:")
        typer.echo(f"  Protein: {macro_ratios['protein']:.1f}%")
        typer.echo(f"  Carbs: {macro_ratios['carbs']:.1f}%")
        typer.echo(f"  Fat: {macro_ratios['fat']:.1f}%")

        # Nutritional balance assessment
        balance = NutritionalAnalyzer.assess_nutritional_balance(nutrition)
        typer.echo(f"\n🎯 Nutritional Balance:")
        typer.echo(f"  Balance Score: {balance['balance_score']}/{balance['max_score']} ({balance['balance_percentage']:.1f}%)")

        if balance['recommendations']:
            typer.echo(f"\n💡 Recommendations:")
            for rec in balance['recommendations']:
                typer.echo(f"  • {rec}")

        if config.debug:
            logger.info(f"Analyzed recipe {recipe_id} nutrition for {servings} servings")

    except Exception as e:
        typer.echo(f"❌ Error analyzing recipe: {e}", err=True)
        if config.debug:
            logger.exception("Error analyzing recipe nutrition")
        raise typer.Exit(1)


@app.command()
def nutrition_summary(
    target_date: Optional[str] = typer.Option(None, "--date", help="Date for analysis (YYYY-MM-DD), defaults to today"),
    period: str = typer.Option("day", "--period", help="Analysis period (day, week, month)"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed breakdown by meal")
):
    """
    Show nutritional summary for a day, week, or month.

    Analyze the nutritional content of all scheduled meals for the specified
    period and provide a comprehensive summary.
    """
    from datetime import datetime, date
    from .nutritional_analysis import NutritionalAnalyzer
    from .calendar_management import CalendarManager

    config = get_config()

    try:
        # Parse target date
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-15)", err=True)
                raise typer.Exit(1)
        else:
            parsed_date = date.today()

        if period.lower() == "day":
            # Daily analysis
            analysis = NutritionalAnalyzer.analyze_daily_nutrition(parsed_date)

            typer.echo(f"🍽️ Daily Nutrition Summary - {analysis['date']}")
            typer.echo("=" * 50)

            if analysis['meal_count'] == 0:
                typer.echo("No meals scheduled for this date.")
                return

            # Total nutrition
            total = analysis['total_nutrition']
            typer.echo(f"\n📊 Total Daily Nutrition:")
            typer.echo(f"  Calories: {total['calories']:.0f}")
            typer.echo(f"  Protein: {total['protein']:.1f}g")
            typer.echo(f"  Carbs: {total['carbs']:.1f}g")
            typer.echo(f"  Fat: {total['fat']:.1f}g")
            typer.echo(f"  Fiber: {total['fiber']:.1f}g")
            typer.echo(f"  Sodium: {total['sodium']:.0f}mg")

            # Meal breakdown
            if detailed and analysis['meal_nutrition']:
                typer.echo(f"\n🍽️ Breakdown by Meal:")
                for meal_type, nutrition in analysis['meal_nutrition'].items():
                    typer.echo(f"  {meal_type.title()}:")
                    typer.echo(f"    Calories: {nutrition['calories']:.0f}")
                    typer.echo(f"    Protein: {nutrition['protein']:.1f}g")
                    typer.echo(f"    Carbs: {nutrition['carbs']:.1f}g")
                    typer.echo(f"    Fat: {nutrition['fat']:.1f}g")

            # Macro ratios
            from .nutritional_analysis import NutritionData
            nutrition_data = NutritionData(**total)
            macro_ratios = NutritionalAnalyzer.calculate_macro_ratios(nutrition_data)
            typer.echo(f"\n⚖️ Macro Ratios:")
            typer.echo(f"  Protein: {macro_ratios['protein']:.1f}%")
            typer.echo(f"  Carbs: {macro_ratios['carbs']:.1f}%")
            typer.echo(f"  Fat: {macro_ratios['fat']:.1f}%")

            # Meal completion
            typer.echo(f"\n✅ Meal Completion: {analysis['completed_meals']}/{analysis['meal_count']} meals completed")

        elif period.lower() == "week":
            # Weekly analysis
            start_date, end_date = CalendarManager.get_week_dates(parsed_date)
            analysis = NutritionalAnalyzer.analyze_period_nutrition(start_date, end_date)

            typer.echo(f"📅 Weekly Nutrition Summary")
            typer.echo(f"Week of {start_date} to {end_date}")
            typer.echo("=" * 50)

            # Average daily nutrition
            avg = analysis['average_daily_nutrition']
            typer.echo(f"\n📊 Average Daily Nutrition:")
            typer.echo(f"  Calories: {avg['calories']:.0f}")
            typer.echo(f"  Protein: {avg['protein']:.1f}g")
            typer.echo(f"  Carbs: {avg['carbs']:.1f}g")
            typer.echo(f"  Fat: {avg['fat']:.1f}g")
            typer.echo(f"  Fiber: {avg['fiber']:.1f}g")
            typer.echo(f"  Sodium: {avg['sodium']:.0f}mg")

            # Weekly totals
            total = analysis['total_nutrition']
            typer.echo(f"\n📈 Weekly Totals:")
            typer.echo(f"  Calories: {total['calories']:.0f}")
            typer.echo(f"  Protein: {total['protein']:.1f}g")
            typer.echo(f"  Carbs: {total['carbs']:.1f}g")
            typer.echo(f"  Fat: {total['fat']:.1f}g")

            # Meal type breakdown
            if analysis['meal_type_totals']:
                typer.echo(f"\n🍽️ Weekly Totals by Meal Type:")
                for meal_type, nutrition in analysis['meal_type_totals'].items():
                    typer.echo(f"  {meal_type.title()}: {nutrition['calories']:.0f} calories")

        elif period.lower() == "month":
            # Monthly analysis
            start_date, end_date = CalendarManager.get_month_dates(parsed_date.year, parsed_date.month)
            analysis = NutritionalAnalyzer.analyze_period_nutrition(start_date, end_date)

            typer.echo(f"📅 Monthly Nutrition Summary")
            typer.echo(f"{parsed_date.strftime('%B %Y')}")
            typer.echo("=" * 50)

            # Average daily nutrition
            avg = analysis['average_daily_nutrition']
            typer.echo(f"\n📊 Average Daily Nutrition:")
            typer.echo(f"  Calories: {avg['calories']:.0f}")
            typer.echo(f"  Protein: {avg['protein']:.1f}g")
            typer.echo(f"  Carbs: {avg['carbs']:.1f}g")
            typer.echo(f"  Fat: {avg['fat']:.1f}g")
            typer.echo(f"  Fiber: {avg['fiber']:.1f}g")
            typer.echo(f"  Sodium: {avg['sodium']:.0f}mg")

            # Monthly totals
            total = analysis['total_nutrition']
            typer.echo(f"\n📈 Monthly Totals:")
            typer.echo(f"  Calories: {total['calories']:.0f}")
            typer.echo(f"  Protein: {total['protein']:.1f}g")
            typer.echo(f"  Days analyzed: {analysis['total_days']}")

        else:
            typer.echo(f"❌ Invalid period. Use 'day', 'week', or 'month'", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Generated {period} nutrition summary for {parsed_date}")

    except Exception as e:
        typer.echo(f"❌ Error generating nutrition summary: {e}", err=True)
        if config.debug:
            logger.exception("Error generating nutrition summary")
        raise typer.Exit(1)


@app.command()
def set_nutrition_goals(
    goal_type: str = typer.Argument(..., help="Goal type (weight_loss, weight_gain, maintenance, muscle_gain, endurance, custom)"),
    daily_calories: float = typer.Argument(..., help="Target daily calories"),
    protein_ratio: Optional[float] = typer.Option(None, "--protein", help="Protein percentage (e.g., 30 for 30%)"),
    carbs_ratio: Optional[float] = typer.Option(None, "--carbs", help="Carbs percentage (e.g., 40 for 40%)"),
    fat_ratio: Optional[float] = typer.Option(None, "--fat", help="Fat percentage (e.g., 30 for 30%)"),
    daily_fiber: Optional[float] = typer.Option(None, "--fiber", help="Daily fiber goal in grams"),
    daily_sodium_max: Optional[float] = typer.Option(None, "--sodium-max", help="Maximum daily sodium in mg")
):
    """
    Set nutritional goals for tracking progress.

    Define your daily nutritional targets based on your health and fitness goals.
    The system will use these goals to track your progress and provide recommendations.
    """
    from .nutritional_goals import GoalType, NutritionalGoalManager

    config = get_config()

    try:
        # Parse goal type
        try:
            parsed_goal_type = GoalType(goal_type.lower())
        except ValueError:
            valid_types = [gt.value for gt in GoalType]
            typer.echo(f"❌ Invalid goal type. Valid options: {', '.join(valid_types)}", err=True)
            raise typer.Exit(1)

        # Validate ratios sum to 100 if all provided
        overrides = {}
        if protein_ratio is not None:
            overrides['protein_ratio'] = protein_ratio
        if carbs_ratio is not None:
            overrides['carbs_ratio'] = carbs_ratio
        if fat_ratio is not None:
            overrides['fat_ratio'] = fat_ratio
        if daily_fiber is not None:
            overrides['daily_fiber'] = daily_fiber
        if daily_sodium_max is not None:
            overrides['daily_sodium_max'] = daily_sodium_max

        # Check if all ratios are provided and sum to 100
        if all(key in overrides for key in ['protein_ratio', 'carbs_ratio', 'fat_ratio']):
            total_ratio = overrides['protein_ratio'] + overrides['carbs_ratio'] + overrides['fat_ratio']
            if abs(total_ratio - 100) > 0.1:
                typer.echo(f"❌ Macro ratios must sum to 100%. Current sum: {total_ratio}%", err=True)
                raise typer.Exit(1)

        # Create goals
        goals = NutritionalGoalManager.create_goals_from_template(
            goal_type=parsed_goal_type,
            daily_calories=daily_calories,
            **overrides
        )

        # Save goals to a simple file (in a real app, this would be in the database)
        import json
        from pathlib import Path

        goals_file = Path("nutrition_goals.json")
        with open(goals_file, 'w') as f:
            json.dump(goals.to_dict(), f, indent=2)

        # Display the goals
        typer.echo("✅ Nutritional goals set successfully!")
        typer.echo(f"\n🎯 Your {goals.goal_type.value.replace('_', ' ').title()} Goals:")
        typer.echo("=" * 50)

        typer.echo(f"\n📊 Daily Targets:")
        typer.echo(f"  Calories: {goals.daily_calories:.0f}")
        typer.echo(f"  Protein: {goals.daily_protein:.1f}g ({goals.protein_ratio:.0f}%)")
        typer.echo(f"  Carbs: {goals.daily_carbs:.1f}g ({goals.carbs_ratio:.0f}%)")
        typer.echo(f"  Fat: {goals.daily_fat:.1f}g ({goals.fat_ratio:.0f}%)")

        if goals.daily_fiber:
            typer.echo(f"  Fiber: {goals.daily_fiber:.0f}g")
        if goals.daily_sodium_max:
            typer.echo(f"  Sodium (max): {goals.daily_sodium_max:.0f}mg")

        typer.echo(f"\n💡 Use 'mealplanner nutrition-progress' to track your progress!")

        if config.debug:
            logger.info(f"Set nutrition goals: {goals.goal_type.value}, {daily_calories} calories")

    except Exception as e:
        typer.echo(f"❌ Error setting nutrition goals: {e}", err=True)
        if config.debug:
            logger.exception("Error setting nutrition goals")
        raise typer.Exit(1)


@app.command()
def nutrition_progress(
    target_date: Optional[str] = typer.Option(None, "--date", help="Date for progress analysis (YYYY-MM-DD), defaults to today"),
    period: str = typer.Option("day", "--period", help="Analysis period (day, week)")
):
    """
    Track progress towards nutritional goals.

    Compare your actual nutrition intake against your set goals and get
    personalized recommendations for improvement.
    """
    from datetime import datetime, date
    from .nutritional_goals import NutritionalGoals, NutritionalGoalManager
    from .nutritional_analysis import NutritionalAnalyzer, NutritionData
    from pathlib import Path
    import json

    config = get_config()

    try:
        # Load goals
        goals_file = Path("nutrition_goals.json")
        if not goals_file.exists():
            typer.echo("❌ No nutrition goals set. Use 'mealplanner set-nutrition-goals' first.", err=True)
            raise typer.Exit(1)

        with open(goals_file, 'r') as f:
            goals_data = json.load(f)

        from .nutritional_goals import GoalType
        goals = NutritionalGoals(
            goal_type=GoalType(goals_data['goal_type']),
            daily_calories=goals_data['daily_calories'],
            daily_protein=goals_data['daily_protein'],
            daily_carbs=goals_data['daily_carbs'],
            daily_fat=goals_data['daily_fat'],
            daily_fiber=goals_data['daily_fiber'],
            daily_sodium_max=goals_data['daily_sodium_max'],
            protein_ratio=goals_data['protein_ratio'],
            carbs_ratio=goals_data['carbs_ratio'],
            fat_ratio=goals_data['fat_ratio']
        )

        # Parse target date
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_date = date.today()

        if period.lower() == "day":
            # Daily progress
            daily_analysis = NutritionalAnalyzer.analyze_daily_nutrition(parsed_date)
            actual_nutrition = NutritionData(**daily_analysis['total_nutrition'])

            progress = NutritionalGoalManager.calculate_progress(goals, actual_nutrition)

            typer.echo(f"📈 Daily Nutrition Progress - {parsed_date}")
            typer.echo(f"Goal: {goals.goal_type.value.replace('_', ' ').title()}")
            typer.echo("=" * 50)

            typer.echo(f"\n🎯 Overall Score: {progress['overall_score']:.1f}/100")

            typer.echo(f"\n📊 Progress Details:")
            for nutrient, data in progress['progress'].items():
                if nutrient == 'sodium':
                    status_emoji = "✅" if data['status'] == 'good' else "⚠️"
                    typer.echo(f"  {status_emoji} {nutrient.title()}: {data['actual']:.0f}mg / {data['target_max']:.0f}mg max ({data['percentage']:.1f}%)")
                else:
                    status_emoji = "✅" if data['status'] == 'good' else ("📉" if data['status'] == 'low' else "📈")
                    typer.echo(f"  {status_emoji} {nutrient.title()}: {data['actual']:.1f} / {data['target']:.1f} ({data['percentage']:.1f}%)")

            # Recommendations
            recommendations = NutritionalGoalManager.generate_recommendations(goals, actual_nutrition)
            if recommendations:
                typer.echo(f"\n💡 Recommendations:")
                for rec in recommendations:
                    typer.echo(f"  • {rec}")

        elif period.lower() == "week":
            # Weekly progress
            weekly_progress = NutritionalGoalManager.analyze_weekly_progress(goals, parsed_date)

            typer.echo(f"📅 Weekly Nutrition Progress")
            typer.echo(f"Week of {weekly_progress['week_start']} to {weekly_progress['week_end']}")
            typer.echo("=" * 50)

            typer.echo(f"\n🎯 Weekly Average Score: {weekly_progress['weekly_progress']['overall_score']:.1f}/100")
            typer.echo(f"📊 Consistency Score: {weekly_progress['consistency_score']:.1f}/100")
            typer.echo(f"📅 Days with data: {weekly_progress['days_with_data']}/7")

            # Weekly averages vs goals
            typer.echo(f"\n📊 Weekly Average Progress:")
            for nutrient, data in weekly_progress['weekly_progress']['progress'].items():
                if nutrient == 'sodium':
                    status_emoji = "✅" if data['status'] == 'good' else "⚠️"
                    typer.echo(f"  {status_emoji} {nutrient.title()}: {data['actual']:.0f}mg avg / {data['target_max']:.0f}mg max")
                else:
                    status_emoji = "✅" if data['status'] == 'good' else ("📉" if data['status'] == 'low' else "📈")
                    typer.echo(f"  {status_emoji} {nutrient.title()}: {data['actual']:.1f} avg / {data['target']:.1f} target")

            # Daily scores
            typer.echo(f"\n📈 Daily Scores:")
            for daily in weekly_progress['daily_progresses']:
                score_emoji = "🟢" if daily['overall_score'] >= 80 else ("🟡" if daily['overall_score'] >= 60 else "🔴")
                typer.echo(f"  {score_emoji} {daily['date']}: {daily['overall_score']:.1f}/100")

        else:
            typer.echo(f"❌ Invalid period. Use 'day' or 'week'", err=True)
            raise typer.Exit(1)

        if config.debug:
            logger.info(f"Generated nutrition progress for {parsed_date}")

    except Exception as e:
        typer.echo(f"❌ Error tracking nutrition progress: {e}", err=True)
        if config.debug:
            logger.exception("Error tracking nutrition progress")
        raise typer.Exit(1)


@app.command()
def generate_shopping_list(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD), defaults to start date"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    format_type: str = typer.Option("text", "--format", "-f", help="Output format (text, csv, json, markdown)"),
    group_by_category: bool = typer.Option(True, "--group-by-category/--no-group", help="Group items by category"),
    include_completed: bool = typer.Option(False, "--include-completed", help="Include completed meals"),
    include_recipes: bool = typer.Option(True, "--include-recipes/--no-recipes", help="Include recipe information"),
    printable: bool = typer.Option(False, "--printable", help="Generate printable format with checkboxes")
):
    """
    Generate a shopping list from scheduled meal plans.

    Create a comprehensive shopping list by aggregating ingredients from all
    scheduled meals within the specified date range.
    """
    from datetime import datetime
    from .shopping_list import ShoppingListGenerator
    from .shopping_list_export import ShoppingListExporter

    config = get_config()

    try:
        # Parse dates
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(f"❌ Invalid start date format. Use YYYY-MM-DD", err=True)
            raise typer.Exit(1)

        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid end date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_end_date = parsed_start_date

        if parsed_end_date < parsed_start_date:
            typer.echo(f"❌ End date cannot be before start date", err=True)
            raise typer.Exit(1)

        # Generate shopping list
        shopping_list = ShoppingListGenerator.generate_from_date_range(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            group_by_category=group_by_category,
            include_completed=include_completed
        )

        if not shopping_list.items:
            typer.echo(f"📝 No ingredients found for the specified date range.")
            typer.echo(f"Make sure you have scheduled meals between {parsed_start_date} and {parsed_end_date}")
            return

        # Generate output
        if printable:
            content = ShoppingListExporter.create_printable_list(
                shopping_list=shopping_list,
                checkboxes=True,
                group_by_category=group_by_category
            )
        elif format_type.lower() == "text":
            content = ShoppingListExporter.export_to_text(
                shopping_list=shopping_list,
                group_by_category=group_by_category,
                include_recipes=include_recipes,
                include_summary=True
            )
        elif format_type.lower() == "csv":
            content = ShoppingListExporter.export_to_csv(shopping_list)
        elif format_type.lower() == "json":
            content = ShoppingListExporter.export_to_json(shopping_list, include_metadata=True)
        elif format_type.lower() == "markdown":
            content = ShoppingListExporter.export_to_markdown(
                shopping_list=shopping_list,
                group_by_category=group_by_category,
                include_recipes=include_recipes
            )
        else:
            typer.echo(f"❌ Unsupported format: {format_type}. Use text, csv, json, or markdown", err=True)
            raise typer.Exit(1)

        # Output to file or console
        if output_file:
            success = ShoppingListExporter.save_to_file(
                shopping_list=shopping_list,
                file_path=output_file,
                format_type=format_type,
                group_by_category=group_by_category,
                include_recipes=include_recipes
            )

            if success:
                typer.echo(f"✅ Shopping list saved to {output_file}")
                typer.echo(f"📊 Summary: {len(shopping_list.items)} items from {shopping_list.total_meals} meals")
            else:
                typer.echo(f"❌ Failed to save shopping list to {output_file}", err=True)
                raise typer.Exit(1)
        else:
            # Output to console
            typer.echo(content)

        if config.debug:
            logger.info(f"Generated shopping list for {parsed_start_date} to {parsed_end_date}")

    except Exception as e:
        typer.echo(f"❌ Error generating shopping list: {e}", err=True)
        if config.debug:
            logger.exception("Error generating shopping list")
        raise typer.Exit(1)


@app.command()
def shopping_list_from_recipes(
    recipe_ids: str = typer.Argument(..., help="Comma-separated recipe IDs"),
    servings: Optional[str] = typer.Option(None, "--servings", help="Comma-separated servings per recipe (e.g., '2,1,3')"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    format_type: str = typer.Option("text", "--format", "-f", help="Output format (text, csv, json, markdown)"),
    group_by_category: bool = typer.Option(True, "--group-by-category/--no-group", help="Group items by category")
):
    """
    Generate a shopping list from specific recipes.

    Create a shopping list by aggregating ingredients from the specified recipes,
    useful for meal prep or cooking multiple recipes at once.
    """
    from .shopping_list import ShoppingListGenerator
    from .shopping_list_export import ShoppingListExporter

    config = get_config()

    try:
        # Parse recipe IDs
        try:
            recipe_id_list = [int(rid.strip()) for rid in recipe_ids.split(',')]
        except ValueError:
            typer.echo(f"❌ Invalid recipe IDs. Use comma-separated integers (e.g., '1,2,3')", err=True)
            raise typer.Exit(1)

        # Parse servings if provided
        servings_per_recipe = {}
        if servings:
            try:
                servings_list = [int(s.strip()) for s in servings.split(',')]
                if len(servings_list) != len(recipe_id_list):
                    typer.echo(f"❌ Number of servings must match number of recipes", err=True)
                    raise typer.Exit(1)
                servings_per_recipe = dict(zip(recipe_id_list, servings_list))
            except ValueError:
                typer.echo(f"❌ Invalid servings. Use comma-separated integers (e.g., '2,1,3')", err=True)
                raise typer.Exit(1)

        # Generate shopping list
        shopping_list = ShoppingListGenerator.generate_from_recipes(
            recipe_ids=recipe_id_list,
            servings_per_recipe=servings_per_recipe
        )

        if not shopping_list.items:
            typer.echo(f"📝 No ingredients found for the specified recipes.")
            typer.echo(f"Make sure the recipe IDs are valid and contain ingredients.")
            return

        # Generate output
        if format_type.lower() == "text":
            content = ShoppingListExporter.export_to_text(
                shopping_list=shopping_list,
                group_by_category=group_by_category,
                include_recipes=True,
                include_summary=True
            )
        elif format_type.lower() == "csv":
            content = ShoppingListExporter.export_to_csv(shopping_list)
        elif format_type.lower() == "json":
            content = ShoppingListExporter.export_to_json(shopping_list, include_metadata=True)
        elif format_type.lower() == "markdown":
            content = ShoppingListExporter.export_to_markdown(
                shopping_list=shopping_list,
                group_by_category=group_by_category,
                include_recipes=True
            )
        else:
            typer.echo(f"❌ Unsupported format: {format_type}. Use text, csv, json, or markdown", err=True)
            raise typer.Exit(1)

        # Output to file or console
        if output_file:
            success = ShoppingListExporter.save_to_file(
                shopping_list=shopping_list,
                file_path=output_file,
                format_type=format_type,
                group_by_category=group_by_category,
                include_recipes=True
            )

            if success:
                typer.echo(f"✅ Shopping list saved to {output_file}")
                typer.echo(f"📊 Summary: {len(shopping_list.items)} items from {len(recipe_id_list)} recipes")
            else:
                typer.echo(f"❌ Failed to save shopping list to {output_file}", err=True)
                raise typer.Exit(1)
        else:
            # Output to console
            typer.echo(content)

        if config.debug:
            logger.info(f"Generated shopping list from recipes: {recipe_id_list}")

    except Exception as e:
        typer.echo(f"❌ Error generating shopping list from recipes: {e}", err=True)
        if config.debug:
            logger.exception("Error generating shopping list from recipes")
        raise typer.Exit(1)


@app.command()
def shopping_list_nutrition(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD), defaults to start date"),
    include_completed: bool = typer.Option(False, "--include-completed", help="Include completed meals")
):
    """
    Analyze the nutritional content of a shopping list.

    Calculate the approximate nutritional value of all ingredients in a
    shopping list generated from scheduled meals.
    """
    from datetime import datetime
    from .shopping_list import ShoppingListGenerator

    config = get_config()

    try:
        # Parse dates
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(f"❌ Invalid start date format. Use YYYY-MM-DD", err=True)
            raise typer.Exit(1)

        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                typer.echo(f"❌ Invalid end date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(1)
        else:
            parsed_end_date = parsed_start_date

        # Generate shopping list
        shopping_list = ShoppingListGenerator.generate_from_date_range(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            include_completed=include_completed
        )

        if not shopping_list.items:
            typer.echo(f"📝 No ingredients found for the specified date range.")
            return

        # Calculate nutrition
        nutrition = ShoppingListGenerator.calculate_shopping_list_nutrition(shopping_list)

        # Display results
        if shopping_list.start_date == shopping_list.end_date:
            date_range = shopping_list.start_date.strftime("%Y-%m-%d")
        else:
            date_range = f"{shopping_list.start_date.strftime('%Y-%m-%d')} to {shopping_list.end_date.strftime('%Y-%m-%d')}"

        typer.echo(f"🛒 Shopping List Nutrition Analysis")
        typer.echo(f"📅 Date Range: {date_range}")
        typer.echo("=" * 50)

        typer.echo(f"\n📊 Total Nutritional Content:")
        typer.echo(f"  Calories: {nutrition['calories']:.0f}")
        typer.echo(f"  Protein: {nutrition['protein']:.1f}g")
        typer.echo(f"  Carbohydrates: {nutrition['carbs']:.1f}g")
        typer.echo(f"  Fat: {nutrition['fat']:.1f}g")
        typer.echo(f"  Fiber: {nutrition['fiber']:.1f}g")
        typer.echo(f"  Sodium: {nutrition['sodium']:.0f}mg")

        typer.echo(f"\n📋 Shopping List Summary:")
        typer.echo(f"  Total Items: {len(shopping_list.items)}")
        typer.echo(f"  Total Meals: {shopping_list.total_meals}")
        typer.echo(f"  Total Recipes: {shopping_list.total_recipes}")
        typer.echo(f"  Categories: {len(shopping_list.categories)}")

        if shopping_list.categories:
            typer.echo(f"  Category List: {', '.join(shopping_list.categories)}")

        typer.echo(f"\n💡 Note: Nutritional values are approximate and based on ingredient data.")
        typer.echo(f"Actual values may vary based on preparation methods and specific brands.")

        if config.debug:
            logger.info(f"Analyzed shopping list nutrition for {parsed_start_date} to {parsed_end_date}")

    except Exception as e:
        typer.echo(f"❌ Error analyzing shopping list nutrition: {e}", err=True)
        if config.debug:
            logger.exception("Error analyzing shopping list nutrition")
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
