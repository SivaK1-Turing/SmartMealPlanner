# Smart Meal Planner

A command-line Python application that helps users import, organize, and schedule recipes into weekly meal plans. It offers ingredient-based search, nutritional analysis, shopping list export, and automated email reminders.

## Features

The Smart Meal Planner is built with a modular design of eight incremental features:

1. **Scaffolding & CLI Setup** ✅ (Implemented)
2. **Database & ORM Integration** ✅ (Implemented)
3. **Recipe Import & Management** (Coming soon)
4. **Ingredient Search & Filtering** (Coming soon)
5. **Meal Scheduling & Calendar** (Coming soon)
6. **Nutritional Analysis** (Coming soon)
7. **Shopping List Export** (Coming soon)
8. **Email Notifications & Packaging** (Coming soon)

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

### Testing Features 1 & 2

Test the CLI and database functionality:

```bash
# Basic functionality
mealplanner --help
mealplanner --version
mealplanner hello

# Database commands (Feature 2)
mealplanner init-db
mealplanner db-info
mealplanner init-db --force  # Recreate database

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
# Run all tests (128 tests total)
pytest tests/ -v

# Run with coverage (91.78% coverage achieved)
pytest tests/ --cov=src/mealplanner --cov-report=term-missing

# Test specific components
pytest tests/test_cli.py -v          # 20 tests - CLI functionality
pytest tests/test_config.py -v       # 22 tests - Configuration management
pytest tests/test_database.py -v     # 24 tests - Database functionality
pytest tests/test_health.py -v       # 23 tests - Health checks
pytest tests/test_models.py -v       # 18 tests - ORM models
pytest tests/test_plugin_loader.py -v # 21 tests - Plugin system

# Run tests with detailed output
pytest tests/ -v --tb=long

# Run specific test methods
pytest tests/test_cli.py::TestCLIBasics::test_help_output -v
```
