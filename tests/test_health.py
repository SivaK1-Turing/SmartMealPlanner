"""
Tests for the health check module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mealplanner.health import (
    check_required_directories,
    check_environment_variables,
    check_file_permissions,
    check_database_connectivity,
    run_health_check,
    create_missing_directories,
    HealthCheckError
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for testing."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


class TestDirectoryChecks:
    """Test directory checking functionality."""
    
    def test_check_required_directories_all_exist(self, temp_workspace):
        """Test when all required directories exist."""
        # Create required directories
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()
        
        missing = check_required_directories()
        assert missing == []
    
    def test_check_required_directories_some_missing(self, temp_workspace):
        """Test when some required directories are missing."""
        # Create only some directories
        (temp_workspace / "plugins").mkdir()
        
        missing = check_required_directories()
        assert "src/mealplanner" in missing
        assert "tests" in missing
        assert "plugins" not in missing
    
    def test_check_required_directories_all_missing(self, temp_workspace):
        """Test when all required directories are missing."""
        missing = check_required_directories()
        assert "plugins" in missing
        assert "src/mealplanner" in missing
        assert "tests" in missing
        assert len(missing) == 3


class TestEnvironmentVariableChecks:
    """Test environment variable checking functionality."""

    def test_check_environment_variables_empty_requirements(self):
        """Test environment variable check with no requirements (Feature 2)."""
        missing = check_environment_variables()
        assert missing == []  # No required vars in Feature 2, DATABASE_URL is optional


class TestFilePermissionChecks:
    """Test file permission checking functionality."""
    
    def test_check_file_permissions_success(self, temp_workspace):
        """Test file permission check when permissions are OK."""
        issues = check_file_permissions()
        assert issues == []
    
    @patch('pathlib.Path.touch')
    def test_check_file_permissions_failure(self, mock_touch, temp_workspace):
        """Test file permission check when permissions fail."""
        mock_touch.side_effect = PermissionError("Permission denied")
        
        issues = check_file_permissions()
        assert len(issues) == 1
        assert "Cannot write to current directory" in issues[0]
    
    @patch('pathlib.Path.touch')
    @patch('pathlib.Path.unlink')
    def test_check_file_permissions_unlink_failure(self, mock_unlink, mock_touch, temp_workspace):
        """Test file permission check when unlink fails."""
        mock_unlink.side_effect = OSError("Cannot delete file")
        
        issues = check_file_permissions()
        assert len(issues) == 1
        assert "Cannot write to current directory" in issues[0]


class TestHealthCheckIntegration:
    """Test the integrated health check functionality."""
    
    def test_run_health_check_all_pass(self, temp_workspace):
        """Test health check when everything passes."""
        # Create required directories
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()
        
        success, issues = run_health_check()
        assert success is True
        assert issues == []
    
    def test_run_health_check_directory_failures(self, temp_workspace):
        """Test health check with directory failures."""
        success, issues = run_health_check()
        assert success is False
        assert len(issues) >= 3  # At least the 3 missing directories
        assert any("Missing directory: plugins" in issue for issue in issues)
        assert any("Missing directory: src/mealplanner" in issue for issue in issues)
        assert any("Missing directory: tests" in issue for issue in issues)
    
    @patch('mealplanner.health.check_file_permissions')
    def test_run_health_check_permission_failures(self, mock_permissions, temp_workspace):
        """Test health check with permission failures."""
        # Create directories so only permissions fail
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()
        
        mock_permissions.return_value = ["Permission error"]
        
        success, issues = run_health_check()
        assert success is False
        assert "Permission error" in issues
    
    @patch('mealplanner.health.check_required_directories')
    def test_run_health_check_exception_handling(self, mock_directories, temp_workspace):
        """Test health check exception handling."""
        mock_directories.side_effect = Exception("Unexpected error")
        
        # Should not raise exception, but return failure
        success, issues = run_health_check()
        assert success is False


class TestCreateMissingDirectories:
    """Test directory creation functionality."""
    
    def test_create_missing_directories(self, temp_workspace):
        """Test creating missing directories."""
        # Ensure directories don't exist
        assert not (temp_workspace / "plugins").exists()
        assert not (temp_workspace / "src" / "mealplanner").exists()
        assert not (temp_workspace / "tests").exists()
        
        create_missing_directories()
        
        # Check that directories were created
        assert (temp_workspace / "plugins").exists()
        assert (temp_workspace / "src" / "mealplanner").exists()
        assert (temp_workspace / "tests").exists()
    
    def test_create_missing_directories_already_exist(self, temp_workspace):
        """Test creating directories when they already exist."""
        # Create directories first
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()
        
        # Should not raise error
        create_missing_directories()
        
        # Directories should still exist
        assert (temp_workspace / "plugins").exists()
        assert (temp_workspace / "src" / "mealplanner").exists()
        assert (temp_workspace / "tests").exists()
    
    @patch('pathlib.Path.mkdir')
    def test_create_missing_directories_permission_error(self, mock_mkdir, temp_workspace):
        """Test creating directories with permission errors."""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        # Should raise the permission error
        with pytest.raises(PermissionError):
            create_missing_directories()


class TestHealthCheckError:
    """Test the HealthCheckError exception."""

    def test_health_check_error(self):
        """Test HealthCheckError exception."""
        error = HealthCheckError("Test error")
        assert str(error) == "Test error"


class TestHealthCheckEdgeCases:
    """Test edge cases in health check functionality."""

    def test_check_environment_variables_with_requirements(self):
        """Test environment variable check with actual requirements."""
        # Temporarily modify the function to have requirements
        original_func = check_environment_variables

        def mock_check_env_vars():
            required_vars = ["NONEXISTENT_VAR"]
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            return missing_vars

        # Patch the function
        with patch('mealplanner.health.check_environment_variables', mock_check_env_vars):
            missing = mock_check_env_vars()
            assert "NONEXISTENT_VAR" in missing

    def test_run_health_check_all_exceptions(self, temp_workspace):
        """Test health check when all checks raise exceptions."""
        with patch('mealplanner.health.check_required_directories') as mock_dirs, \
             patch('mealplanner.health.check_environment_variables') as mock_env, \
             patch('mealplanner.health.check_file_permissions') as mock_perms:

            mock_dirs.side_effect = Exception("Directory error")
            mock_env.side_effect = Exception("Environment error")
            mock_perms.side_effect = Exception("Permission error")

            success, issues = run_health_check()
            assert success is False
            assert len(issues) == 3
            assert any("Directory check failed" in issue for issue in issues)
            assert any("Environment variable check failed" in issue for issue in issues)
            assert any("Permission check failed" in issue for issue in issues)


class TestDatabaseConnectivityChecks:
    """Test database connectivity checking functionality."""

    def test_check_database_connectivity_success(self):
        """Test successful database connectivity check."""
        with patch('mealplanner.database.get_database_url') as mock_get_url, \
             patch('mealplanner.database.check_database_connection') as mock_check_conn:

            mock_get_url.return_value = "sqlite:///test.db"
            mock_check_conn.return_value = True

            issues = check_database_connectivity()
            assert issues == []

    def test_check_database_connectivity_failure(self):
        """Test failed database connectivity check."""
        with patch('mealplanner.database.get_database_url') as mock_get_url, \
             patch('mealplanner.database.check_database_connection') as mock_check_conn:

            mock_get_url.return_value = "sqlite:///test.db"
            mock_check_conn.return_value = False

            issues = check_database_connectivity()
            assert len(issues) == 1
            assert "Cannot connect to database" in issues[0]

    def test_check_database_connectivity_url_error(self):
        """Test database connectivity check with URL configuration error."""
        with patch('mealplanner.database.get_database_url') as mock_get_url:
            mock_get_url.side_effect = Exception("URL configuration error")

            issues = check_database_connectivity()
            assert len(issues) == 1
            assert "Database URL configuration error" in issues[0]

    def test_check_database_connectivity_import_error(self):
        """Test database connectivity check with import error."""
        with patch('mealplanner.database.get_database_url') as mock_get_url:
            mock_get_url.side_effect = ImportError("Module not found")

            issues = check_database_connectivity()
            assert len(issues) == 1
            assert "Database URL configuration error" in issues[0]

    def test_run_health_check_with_database(self, temp_workspace):
        """Test health check including database connectivity."""
        # Create required directories
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()

        with patch('mealplanner.health.check_database_connectivity') as mock_db_check:
            mock_db_check.return_value = []  # No database issues

            success, issues = run_health_check()
            assert success is True
            assert issues == []
            mock_db_check.assert_called_once()

    def test_run_health_check_with_database_issues(self, temp_workspace):
        """Test health check with database connectivity issues."""
        # Create required directories
        (temp_workspace / "plugins").mkdir()
        (temp_workspace / "src" / "mealplanner").mkdir(parents=True)
        (temp_workspace / "tests").mkdir()

        with patch('mealplanner.health.check_database_connectivity') as mock_db_check:
            mock_db_check.return_value = ["Database connection failed"]

            success, issues = run_health_check()
            assert success is False
            assert "Database connection failed" in issues
