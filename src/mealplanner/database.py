"""
Database configuration and session management for the Smart Meal Planner application.

Handles SQLite and PostgreSQL connections, session management, and database initialization.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import get_config
from .models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    """
    Get database URL from configuration.
    
    Returns:
        Database URL string
        
    Raises:
        ValueError: If DATABASE_URL is not configured
    """
    config = get_config()
    database_url = config.get('DATABASE_URL')
    
    if not database_url:
        # Default to SQLite in the current directory
        database_url = 'sqlite:///mealplanner.db'
        logger.warning(f"DATABASE_URL not configured, using default: {database_url}")
    
    return database_url


def create_database_engine(database_url: Optional[str] = None) -> Engine:
    """
    Create and configure database engine.
    
    Args:
        database_url: Optional database URL override
        
    Returns:
        Configured SQLAlchemy engine
        
    Raises:
        ValueError: If database URL is invalid
        OperationalError: If database connection fails
    """
    if database_url is None:
        database_url = get_database_url()
    
    logger.info(f"Creating database engine for: {database_url}")
    
    # Configure engine based on database type
    if database_url.startswith('sqlite'):
        # SQLite-specific configuration
        engine = create_engine(
            database_url,
            echo=get_config().debug,  # Log SQL queries in debug mode
            poolclass=StaticPool,
            connect_args={
                'check_same_thread': False,  # Allow multiple threads
                'timeout': 30  # 30 second timeout
            }
        )
        
        # Enable foreign key constraints for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    elif database_url.startswith('postgresql'):
        # PostgreSQL-specific configuration
        engine = create_engine(
            database_url,
            echo=get_config().debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600    # Recycle connections after 1 hour
        )
    else:
        # Generic configuration for other databases
        engine = create_engine(
            database_url,
            echo=get_config().debug
        )
    
    # Test the connection
    try:
        with engine.connect() as conn:
            logger.info("Database connection successful")
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise OperationalError(
            f"Cannot connect to database. Please check your DATABASE_URL configuration.",
            None, None
        ) from e
    
    return engine


def get_engine() -> Engine:
    """
    Get the global database engine, creating it if necessary.
    
    Returns:
        Database engine instance
    """
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get the global session factory, creating it if necessary.
    
    Returns:
        Session factory
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.
    
    Provides a database session that automatically:
    - Commits on successful completion
    - Rolls back on exceptions
    - Closes the session in all cases
    
    Yields:
        Database session
        
    Example:
        with get_db_session() as session:
            recipe = Recipe(title="Test Recipe")
            session.add(recipe)
            # Automatically commits here
    """
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        logger.debug("Database session started")
        yield session
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        logger.error(f"Database session error, rolling back: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


def create_tables(engine: Optional[Engine] = None) -> None:
    """
    Create all database tables.
    
    Args:
        engine: Optional engine override
    """
    if engine is None:
        engine = get_engine()
    
    try:
        logger.info("Creating database tables")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_tables(engine: Optional[Engine] = None) -> None:
    """
    Drop all database tables.
    
    Args:
        engine: Optional engine override
        
    Warning:
        This will delete all data in the database!
    """
    if engine is None:
        engine = get_engine()
    
    try:
        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(engine)
        logger.warning("All database tables dropped")
    except SQLAlchemyError as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def init_database(database_url: Optional[str] = None, force: bool = False) -> None:
    """
    Initialize the database by creating tables.
    
    Args:
        database_url: Optional database URL override
        force: If True, drop existing tables first
        
    Raises:
        OperationalError: If database initialization fails
    """
    try:
        if database_url:
            # Create a new engine for the specified URL
            engine = create_database_engine(database_url)
        else:
            engine = get_engine()
        
        if force:
            logger.warning("Force initialization: dropping existing tables")
            drop_tables(engine)
        
        # Check if tables already exist
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()

            if existing_tables and not force:
                logger.info(f"Database already initialized with tables: {existing_tables}")
                return
        except (ImportError, Exception):
            # If inspect is not available or fails, just try to create tables
            logger.debug("Could not inspect existing tables, proceeding with table creation")
        
        create_tables(engine)
        logger.info("Database initialization completed")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise OperationalError(
            f"Failed to initialize database: {e}",
            None, None
        ) from e


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect():
            logger.debug("Database connection check successful")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get information about the current database configuration.
    
    Returns:
        Dictionary with database information
    """
    try:
        engine = get_engine()
        database_url = str(engine.url)
        
        # Hide password in URL for logging
        safe_url = database_url
        if '@' in database_url:
            parts = database_url.split('@')
            if len(parts) == 2:
                user_pass = parts[0].split('://')[-1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    safe_url = database_url.replace(user_pass, f"{user}:***")
        
        info = {
            'database_url': safe_url,
            'driver': engine.dialect.name,
            'connected': check_database_connection()
        }
        
        # Add SQLite-specific info
        if engine.dialect.name == 'sqlite':
            db_path = database_url.replace('sqlite:///', '')
            info['database_file'] = db_path
            info['file_exists'] = Path(db_path).exists()
            if Path(db_path).exists():
                info['file_size'] = Path(db_path).stat().st_size
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {'error': str(e)}


# Cleanup function for testing
def reset_database_globals():
    """Reset global database variables. Used for testing."""
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
    _engine = None
    _session_factory = None
