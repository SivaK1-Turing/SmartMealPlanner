"""
Tests for the database module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError

from mealplanner.database import (
    get_database_url, create_database_engine, get_engine, get_session_factory,
    get_db_session, create_tables, drop_tables, init_database,
    check_database_connection, get_database_info, reset_database_globals
)


@pytest.fixture
def clean_env():
    """Clean environment variables for testing."""
    original_env = os.environ.copy()
    # Clear database-related environment variables
    for key in list(os.environ.keys()):
        if key.startswith('DATABASE'):
            del os.environ[key]
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch('mealplanner.database.get_config') as mock_get_config:
        mock_config_obj = MagicMock()
        mock_config_obj.debug = False
        mock_config_obj.get.return_value = None
        mock_get_config.return_value = mock_config_obj
        yield mock_config_obj


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global database variables before each test."""
    reset_database_globals()
    yield
    reset_database_globals()


class TestDatabaseURL:
    """Test database URL configuration."""
    
    def test_get_database_url_from_config(self, mock_config):
        """Test getting database URL from configuration."""
        mock_config.get.return_value = "sqlite:///test.db"
        
        url = get_database_url()
        assert url == "sqlite:///test.db"
        mock_config.get.assert_called_once_with('DATABASE_URL')
    
    def test_get_database_url_default(self, mock_config):
        """Test default database URL when not configured."""
        mock_config.get.return_value = None
        
        url = get_database_url()
        assert url == "sqlite:///mealplanner.db"
    
    def test_get_database_url_from_env(self, clean_env, mock_config):
        """Test getting database URL from environment variable."""
        os.environ['DATABASE_URL'] = "postgresql://user:pass@localhost/test"
        mock_config.get.return_value = "postgresql://user:pass@localhost/test"
        
        url = get_database_url()
        assert url == "postgresql://user:pass@localhost/test"


class TestEngineCreation:
    """Test database engine creation."""
    
    def test_create_sqlite_engine(self, mock_config):
        """Test creating SQLite engine."""
        mock_config.debug = False
        
        engine = create_database_engine("sqlite:///:memory:")
        assert engine is not None
        assert engine.dialect.name == "sqlite"
    
    def test_create_sqlite_engine_debug(self, mock_config):
        """Test creating SQLite engine with debug mode."""
        mock_config.debug = True
        
        engine = create_database_engine("sqlite:///:memory:")
        assert engine.echo is True
    
    @patch('mealplanner.database.create_engine')
    def test_create_postgresql_engine(self, mock_create_engine, mock_config):
        """Test creating PostgreSQL engine configuration."""
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = create_database_engine("postgresql://user:pass@localhost/test")
        
        # Verify create_engine was called with PostgreSQL-specific options
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql://user:pass@localhost/test"
        assert 'pool_size' in call_args[1]
        assert 'max_overflow' in call_args[1]
        assert 'pool_pre_ping' in call_args[1]
    
    def test_create_engine_connection_failure(self, mock_config):
        """Test engine creation with connection failure."""
        # Use a directory path instead of a file to cause connection failure
        with pytest.raises(OperationalError, match="Cannot connect to database"):
            create_database_engine("sqlite:///nonexistent_directory/invalid.db")
    
    def test_get_engine_singleton(self, mock_config):
        """Test that get_engine returns the same instance."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2
    
    def test_get_session_factory_singleton(self, mock_config):
        """Test that get_session_factory returns the same instance."""
        factory1 = get_session_factory()
        factory2 = get_session_factory()
        assert factory1 is factory2


class TestSessionManagement:
    """Test database session management."""
    
    def test_session_context_manager_success(self, mock_config):
        """Test successful session context manager."""
        with get_db_session() as session:
            assert session is not None
            # Session should be active
            assert session.is_active
    
    def test_session_context_manager_exception(self, mock_config):
        """Test session context manager with exception."""
        with pytest.raises(ValueError):
            with get_db_session() as session:
                # Simulate an error
                raise ValueError("Test error")
        
        # Session should be closed even after exception
    
    @patch('mealplanner.database.get_session_factory')
    def test_session_rollback_on_exception(self, mock_factory, mock_config):
        """Test that session rolls back on exception."""
        mock_session = MagicMock()
        mock_factory.return_value.return_value = mock_session
        
        with pytest.raises(ValueError):
            with get_db_session() as session:
                raise ValueError("Test error")
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestTableOperations:
    """Test table creation and dropping operations."""
    
    @patch('mealplanner.database.Base')
    def test_create_tables(self, mock_base, mock_config):
        """Test table creation."""
        mock_engine = MagicMock()
        
        create_tables(mock_engine)
        
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)
    
    @patch('mealplanner.database.Base')
    def test_drop_tables(self, mock_base, mock_config):
        """Test table dropping."""
        mock_engine = MagicMock()
        
        drop_tables(mock_engine)
        
        mock_base.metadata.drop_all.assert_called_once_with(mock_engine)
    
    @patch('mealplanner.database.Base')
    def test_create_tables_error(self, mock_base, mock_config):
        """Test table creation with error."""
        mock_base.metadata.create_all.side_effect = Exception("Table creation failed")
        mock_engine = MagicMock()
        
        with pytest.raises(Exception, match="Table creation failed"):
            create_tables(mock_engine)


class TestDatabaseInitialization:
    """Test database initialization."""
    
    @patch('mealplanner.database.create_tables')
    @patch('mealplanner.database.get_engine')
    def test_init_database_basic(self, mock_get_engine, mock_create_tables, mock_config):
        """Test basic database initialization."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        # Mock the inspect to return no existing tables
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = []
            mock_inspect.return_value = mock_inspector

            init_database()

            mock_create_tables.assert_called_once_with(mock_engine)
    
    @patch('mealplanner.database.drop_tables')
    @patch('mealplanner.database.create_tables')
    @patch('mealplanner.database.get_engine')
    def test_init_database_force(self, mock_get_engine, mock_create_tables, mock_drop_tables, mock_config):
        """Test database initialization with force flag."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        init_database(force=True)
        
        mock_drop_tables.assert_called_once_with(mock_engine)
        mock_create_tables.assert_called_once_with(mock_engine)
    
    @patch('mealplanner.database.create_database_engine')
    @patch('mealplanner.database.create_tables')
    def test_init_database_custom_url(self, mock_create_tables, mock_create_engine, mock_config):
        """Test database initialization with custom URL."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock the inspect to return no existing tables
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = []
            mock_inspect.return_value = mock_inspector

            init_database(database_url="sqlite:///custom.db")

            mock_create_engine.assert_called_once_with("sqlite:///custom.db")
            mock_create_tables.assert_called_once_with(mock_engine)
    
    @patch('mealplanner.database.get_engine')
    def test_init_database_existing_tables(self, mock_get_engine, mock_config):
        """Test database initialization with existing tables."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch('sqlalchemy.inspect') as mock_inspect, \
             patch('mealplanner.database.create_tables') as mock_create_tables:

            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = ['recipes', 'ingredients']
            mock_inspect.return_value = mock_inspector

            init_database()
            # Should not create tables if they already exist
            mock_create_tables.assert_not_called()


class TestDatabaseInfo:
    """Test database information functions."""
    
    @patch('mealplanner.database.get_engine')
    def test_check_database_connection_success(self, mock_get_engine, mock_config):
        """Test successful database connection check."""
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        result = check_database_connection()
        assert result is True
    
    @patch('mealplanner.database.get_engine')
    def test_check_database_connection_failure(self, mock_get_engine, mock_config):
        """Test failed database connection check."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection failed")
        mock_get_engine.return_value = mock_engine
        
        result = check_database_connection()
        assert result is False
    
    @patch('mealplanner.database.check_database_connection')
    @patch('mealplanner.database.get_engine')
    def test_get_database_info_sqlite(self, mock_get_engine, mock_check_conn, mock_config):
        """Test getting database info for SQLite."""
        mock_engine = MagicMock()
        mock_engine.url = "sqlite:///test.db"
        mock_engine.dialect.name = "sqlite"
        mock_get_engine.return_value = mock_engine
        mock_check_conn.return_value = True
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            
            info = get_database_info()
            
            assert info['database_url'] == "sqlite:///test.db"
            assert info['driver'] == "sqlite"
            assert info['connected'] is True
            assert info['database_file'] == "test.db"
            assert info['file_exists'] is True
            assert info['file_size'] == 1024
    
    @patch('mealplanner.database.check_database_connection')
    @patch('mealplanner.database.get_engine')
    def test_get_database_info_postgresql(self, mock_get_engine, mock_check_conn, mock_config):
        """Test getting database info for PostgreSQL."""
        mock_engine = MagicMock()
        mock_engine.url = "postgresql://user:password@localhost/test"
        mock_engine.dialect.name = "postgresql"
        mock_get_engine.return_value = mock_engine
        mock_check_conn.return_value = True
        
        info = get_database_info()
        
        # Password should be hidden
        assert "user:***@localhost" in info['database_url']
        assert "password" not in info['database_url']
        assert info['driver'] == "postgresql"
        assert info['connected'] is True
    
    @patch('mealplanner.database.get_engine')
    def test_get_database_info_error(self, mock_get_engine, mock_config):
        """Test getting database info with error."""
        mock_get_engine.side_effect = Exception("Engine error")
        
        info = get_database_info()
        
        assert 'error' in info
        assert "Engine error" in info['error']
