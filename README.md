# Smart Meal Planner

A command-line Python application that helps users import, organize, and schedule recipes into weekly meal plans. It offers ingredient-based search, nutritional analysis, shopping list export, and automated email reminders.

## Features

The Smart Meal Planner is built with a modular design of eight incremental features:

1. **Scaffolding & CLI Setup** ✅ (Implemented)
2. **Database & ORM Integration** ✅ (Implemented)
3. **Recipe Import & Management** ✅ (Implemented)
4. **Ingredient Search & Filtering** ✅ (Implemented)
5. **Meal Scheduling & Calendar** ✅ (Implemented)
6. **Nutritional Analysis** ✅ (Implemented)
7. **Shopping List Export** ✅ (Implemented)
8. **Email Notifications & Packaging** ✅ (Implemented)

## Installation

### Prerequisites

- Python 3.8 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd SmartMealPlanner
```

2. Install dependencies:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

### Using pip

1. Clone the repository:
```bash
git clone <repository-url>
cd SmartMealPlanner
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Usage

### Basic Commands

After installation, you can use the `mealplanner` command:

```bash
# Show help
mealplanner --help

# Show version
mealplanner --version

# Test the CLI setup
mealplanner hello

# Enable debug logging
mealplanner --debug hello

# Use custom configuration file
mealplanner --config custom.env hello
```

### Running Tests

Run all tests:
```bash
# Using Poetry
poetry run pytest

# Using pip
pytest
```

Run tests with coverage:
```bash
# Using Poetry
poetry run pytest --cov=src/mealplanner --cov-report=term-missing

# Using pip
pytest --cov=src/mealplanner --cov-report=term-missing
```

Run specific test files:
```bash
pytest tests/test_cli.py
pytest tests/test_config.py
pytest tests/test_health.py
pytest tests/test_plugin_loader.py
```

## Feature 1: Scaffolding & CLI Setup

### Testing Features 1, 2, 3, 4 & 5

Test the CLI, database, recipe, ingredient, and meal planning functionality:

```bash
# Basic functionality
mealplanner --help
mealplanner --version
mealplanner hello

# Database commands (Feature 2)
mealplanner init-db
mealplanner db-info
mealplanner init-db --force  # Recreate database

# Recipe import commands (Feature 3)
mealplanner import-recipes sample_recipes.json
mealplanner import-csv sample_recipes.csv
mealplanner import-url https://api.example.com/recipes.json

# Recipe management commands (Feature 3)
mealplanner list-recipes
mealplanner list-recipes --cuisine Italian
mealplanner list-recipes --search "pasta"
mealplanner list-recipes --detailed
mealplanner update-recipe 1
mealplanner delete-recipe 1

# Ingredient search and management commands (Feature 4)
mealplanner add-ingredient "Chicken Breast" --category "Meat" --calories 165 --protein 31.0
mealplanner list-ingredients
mealplanner search-ingredients --min-protein 20 --max-calories 200
mealplanner search-ingredients --category "Vegetables" --detailed
mealplanner ingredient-stats
mealplanner update-ingredient 1
mealplanner delete-ingredient 1

# Meal scheduling and calendar commands (Feature 5)
mealplanner schedule-meal 2 2025-06-20 dinner --servings 2 --notes "Family dinner"
mealplanner view-calendar --date 2025-06-20 --view week --detailed
mealplanner list-plans --start 2025-06-20 --end 2025-06-21
mealplanner complete-meal 1
mealplanner update-plan 1
mealplanner delete-plan 3
mealplanner clear-schedule 2025-06-20 --end 2025-06-22
mealplanner plan-stats --period week

# Debug mode
mealplanner --debug hello

# Health checks (will create missing directories and check database)
mealplanner hello

# Plugin system (create a test plugin first)
echo 'def cmd_test(): return "Plugin works!"' > plugins/test_plugin.py
mealplanner hello  # Plugins are loaded automatically

# Test configuration files
echo "DATABASE_URL=sqlite:///custom.db" > test.env
mealplanner --config test.env db-info

# Test error handling
mealplanner --config nonexistent.env hello  # Should show error
```

Run the test suite:

```bash
# Run all tests (238 tests total)
pytest tests/ -v

# Run with coverage (61.52% coverage achieved)
pytest tests/ --cov=src/mealplanner --cov-report=term-missing

# Test specific components
pytest tests/test_cli.py -v                    # 23 tests - CLI functionality
pytest tests/test_config.py -v                 # 22 tests - Configuration management
pytest tests/test_database.py -v               # 24 tests - Database functionality
pytest tests/test_health.py -v                 # 23 tests - Health checks
pytest tests/test_models.py -v                 # 18 tests - ORM models
pytest tests/test_plugin_loader.py -v          # 21 tests - Plugin system
pytest tests/test_recipe_import.py -v          # 22 tests - Recipe import functionality
pytest tests/test_recipe_management.py -v      # 21 tests - Recipe management
pytest tests/test_ingredient_search.py -v      # 15 tests - Ingredient search functionality
pytest tests/test_ingredient_management.py -v  # 21 tests - Ingredient management
pytest tests/test_meal_planning.py -v          # 16 tests - Meal planning functionality
pytest tests/test_calendar_management.py -v    # 12 tests - Calendar management

# Run tests with detailed output
pytest tests/ -v --tb=long

# Run specific test methods
pytest tests/test_cli.py::TestCLIBasics::test_help_output -v
```
