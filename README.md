![code_execution1](https://github.com/user-attachments/assets/157a7bf7-0125-4085-b13b-e12525a00e02)# Smart Meal Planner

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

1.Code Execution

![code_execution1](https://github.com/user-attachments/assets/45d6d5d5-fe5f-4363-94ec-0e43524f89f2)

![code_execution2-1](https://github.com/user-attachments/assets/9ee2c411-3c35-4ecc-8fac-49d34ede27f5)

![code_execution2-2](https://github.com/user-attachments/assets/d360dc31-5d7d-4a15-ab90-e2957422c997)

![code_execution2-3](https://github.com/user-attachments/assets/45f9e708-0ce6-4db3-af63-4e7e1d51ed4c)

![code_execution1](https://github.com/user-attachments/assets/f28fc25c-cc0b-43b3-962a-6f4d24c63b23)

![code_execution2](https://github.com/user-attachments/assets/7bca76b9-18ad-467c-8270-b29ee0e950f8)

![Code_execution3](https://github.com/user-attachments/assets/b5bf553e-6d54-431c-9bcf-44e04f265c70)

![code_execution1](https://github.com/user-attachments/assets/60d32823-1399-4248-b507-47492539dc8b)

![code_execution2](https://github.com/user-attachments/assets/b34242d7-e9c3-4be5-ac78-8e8028fbd9d8)

![coide_execution1](https://github.com/user-attachments/assets/24ec1765-f9ba-46b2-88bb-a4df91bb56a9)

![code_execution2](https://github.com/user-attachments/assets/b9f60f95-2b5e-40fb-b76b-e475d3bba35d)

![code_execution3](https://github.com/user-attachments/assets/5b7c75d5-a2ee-4d7b-9eea-db58ecc4416c)

![code_execution1](https://github.com/user-attachments/assets/5d16c552-11bb-4ec6-be87-1bf841ec98d5)

![code_execution2](https://github.com/user-attachments/assets/31ce215c-15e6-4ca4-91c9-2e3aa3995ef0)

![code_execution3](https://github.com/user-attachments/assets/88b01e2b-de7d-4881-9a49-b6c4bc8369ef)

![code_execution1](https://github.com/user-attachments/assets/428bc198-d471-4cc1-9de0-4d0e87e7bd9e)

![code_execution1](https://github.com/user-attachments/assets/582810e8-9c04-4889-933f-1079cc24c655)

![code_execution2](https://github.com/user-attachments/assets/1216841b-b765-48a6-a752-da24763d8d5e)

2. Test Execution

![test_execution1](https://github.com/user-attachments/assets/06ecb276-52df-4b46-ba7e-0c34f76ed249)

![test_execution2-1](https://github.com/user-attachments/assets/e971870b-c416-42a9-b958-932274bdf70a)

![test_execution2-2](https://github.com/user-attachments/assets/d29ed66f-5954-4391-b2d6-61291b21ef48)

![test_execution3](https://github.com/user-attachments/assets/3023eb15-f8ca-4ee6-b0c7-5ebf1e58b4a8)

![test_execution1](https://github.com/user-attachments/assets/019b3359-50b0-450b-9ad1-3886fb3ecf46)

![test_execution2](https://github.com/user-attachments/assets/00d055b6-43b5-4f0e-a294-7d45e904fd56)

![test_execution1](https://github.com/user-attachments/assets/651abe2f-d151-4078-9ec3-0f5b46c2c6b1)

![test_execution2](https://github.com/user-attachments/assets/652e9aa8-3887-4d36-907a-b11c9092fd03)

![test_execution1](https://github.com/user-attachments/assets/26f0a1d0-ed6a-455c-96e9-54e9d625cae9)

![test_execcution2](https://github.com/user-attachments/assets/506bc31e-a2fe-4258-9bbd-bb3fa8ba0f80)

![test_execution1](https://github.com/user-attachments/assets/de4076ae-caec-498c-858b-ae8f4e70e93e)

![test_execution](https://github.com/user-attachments/assets/7c07d267-d8d8-45f2-8b41-a76f191a0c51)

**Project Features Mapped to Conversations**

- Conversation 1: Feature 1 establishes a Poetry-based project structure with src/, tests/, and plugins/ directories. It configures a Typer-powered CLI including version flag, environment-variable loading, JSON logging, dynamic plugin registration, graceful handling of unknown commands, pre-run health-check routines, and generated help output.
  
- Conversation 2: Feature 2 integrates SQLAlchemy ORM with Recipe, Ingredient, and Plan models, an environment-configurable DATABASE_URL, and a session context manager supporting nested transactions and connection pooling. It includes Alembic migration scaffolding, an init-db command, health-check endpoint, and switchable SQLite or PostgreSQL backends.

- Conversation 3: Feature 3 adds robust recipe import commands for JSON, CSV, and HTTP URL sources. It performs schema validation, fuzzy-title deduplication with interactive prompts, dry-run mode, atomic transactions with rollback, and migration-safe cascading deletes. Comprehensive pytest coverage mocks file I/O calls.
  
- Conversation 4: Feature 4 delivers a sophisticated search-recipes command supporting full-text and fuzzy matching on titles, ingredients, and tags. It provides include/exclude filters, cursor-based pagination with adjustable thresholds, sort and group options, no-result suggestions, exportable JSON/CSV outputs, and configurable latency logging metrics.

- Conversation 5: Feature 5 introduces flexible meal scheduling with natural-language recurrence parsing into RRULE expressions. It detects conflicts and applies overwrite, skip, or merge strategies, offers calendar-style weekly and monthly displays, supports iCal export, CSV imports, editor-driven plan editing, and retention pruning.

- Conversation 6: Feature 6 computes detailed nutrition summaries over user-defined date ranges. It aggregates calories and macronutrients with Pandas, supports CSV, JSON exports, threshold-based alerts, chunked processing for large windows, cacheable nutrition lookups, imputation for missing values, and Matplotlib charts for breakdowns.

- Conversation 7: Feature 7 generates consolidated shopping lists by aggregating and normalizing ingredient quantities. It supports grouping by recipe or aisle with Jinja2 templating, CSV, Markdown, or JSON outputs, price merging from CSV, progress bars for large lists, and SMTP email delivery.

- Conversation 8: Feature 8 implements templated HTML and plain-text reminder emails with asyncio support, tenacity-powered retries, APScheduler scheduling, and configurable send windows. It supports dry-run and cron-output modes, exposes package entry points, includes CI workflows and automated releases, and end-to-end integration tests.





