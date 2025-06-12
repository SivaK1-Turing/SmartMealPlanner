"""
Health check functionality for the Smart Meal Planner application.

Verifies required directories and environment variables exist before running commands.
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Raised when health checks fail."""
    pass


def check_required_directories() -> List[str]:
    """
    Check that required directories exist.
    
    Returns:
        List of missing directories
    """
    required_dirs = [
        "plugins",
        "src/mealplanner",
        "tests"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
            logger.warning(f"Required directory missing: {dir_path}")
    
    return missing_dirs


def check_environment_variables() -> List[str]:
    """
    Check that required environment variables are set.

    Returns:
        List of missing environment variables
    """
    # For Feature 2, we check database configuration
    required_vars = []  # DATABASE_URL is optional, defaults to SQLite
    recommended_vars = ["DATABASE_URL"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            logger.warning(f"Required environment variable missing: {var}")

    # Check recommended variables
    for var in recommended_vars:
        if not os.getenv(var):
            logger.info(f"Recommended environment variable not set: {var} (will use default)")

    return missing_vars


def check_database_connectivity() -> List[str]:
    """
    Check database connectivity and configuration.

    Returns:
        List of database issues
    """
    issues = []

    try:
        from .database import check_database_connection, get_database_url

        # Check if we can get database URL
        try:
            db_url = get_database_url()
            logger.debug(f"Database URL configured: {db_url}")
        except Exception as e:
            issues.append(f"Database URL configuration error: {e}")
            return issues

        # Check database connectivity
        if not check_database_connection():
            issues.append("Cannot connect to database")
            logger.warning("Database connectivity check failed")
        else:
            logger.debug("Database connectivity check passed")

    except ImportError as e:
        issues.append(f"Database module import error: {e}")
        logger.error(f"Database module import error: {e}")
    except Exception as e:
        issues.append(f"Database check error: {e}")
        logger.error(f"Database check error: {e}")

    return issues


def check_file_permissions() -> List[str]:
    """
    Check that we have appropriate file permissions.
    
    Returns:
        List of permission issues
    """
    permission_issues = []
    
    # Check if we can write to the current directory
    try:
        test_file = Path(".health_check_test")
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        permission_issues.append(f"Cannot write to current directory: {e}")
        logger.warning(f"Permission issue: {e}")
    
    return permission_issues


def run_health_check() -> Tuple[bool, List[str]]:
    """
    Run all health checks.

    Returns:
        Tuple of (success, list of issues)
    """
    logger.info("Running pre-run health checks")

    all_issues = []

    try:
        # Check directories
        missing_dirs = check_required_directories()
        if missing_dirs:
            all_issues.extend([f"Missing directory: {d}" for d in missing_dirs])
    except Exception as e:
        all_issues.append(f"Directory check failed: {e}")
        logger.error(f"Directory check failed: {e}")

    try:
        # Check environment variables
        missing_vars = check_environment_variables()
        if missing_vars:
            all_issues.extend([f"Missing environment variable: {v}" for v in missing_vars])
    except Exception as e:
        all_issues.append(f"Environment variable check failed: {e}")
        logger.error(f"Environment variable check failed: {e}")

    try:
        # Check permissions
        permission_issues = check_file_permissions()
        all_issues.extend(permission_issues)
    except Exception as e:
        all_issues.append(f"Permission check failed: {e}")
        logger.error(f"Permission check failed: {e}")

    try:
        # Check database connectivity
        db_issues = check_database_connectivity()
        all_issues.extend(db_issues)
    except Exception as e:
        all_issues.append(f"Database check failed: {e}")
        logger.error(f"Database check failed: {e}")

    success = len(all_issues) == 0

    if success:
        logger.info("All health checks passed")
    else:
        logger.error(f"Health checks failed with {len(all_issues)} issues")
        for issue in all_issues:
            logger.error(f"  - {issue}")

    return success, all_issues


def create_missing_directories() -> None:
    """Create any missing required directories."""
    required_dirs = [
        "plugins",
        "src/mealplanner", 
        "tests"
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            logger.info(f"Creating missing directory: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
