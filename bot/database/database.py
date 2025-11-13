"""
Database configuration and session management for MySQL storage.
Adapted from GPTIFOBIZ architecture for Ignatova-Stroinost bot.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger
logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("DATABASE_URL not found in environment. Database features will be disabled.")
    DATABASE_ENABLED = False
    engine = None
    SessionLocal = None
    Base = declarative_base()
else:
    DATABASE_ENABLED = True

    # Create engine with connection pooling
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,  # Maximum number of connections to keep open
        max_overflow=20,  # Maximum number of connections to create beyond pool_size
        pool_timeout=30,  # Seconds to wait before giving up on getting a connection
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Verify connections before using them
        echo=False,  # Set to True for SQL query logging
    )

    # Create session factory
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    # Base class for models
    Base = declarative_base()

    logger.info(f"Database engine created successfully: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'MySQL'}")


def get_db():
    """
    Dependency function to get database session.
    Usage in FastAPI endpoints:

    @app.get("/endpoint")
    def endpoint(db: Session = Depends(get_db)):
        ...
    """
    if not DATABASE_ENABLED:
        return None

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """
    if not DATABASE_ENABLED:
        logger.warning("Database is disabled. Skipping table creation.")
        return

    try:
        # Import models to register them with Base
        from bot.database.models import TelegramChat, TelegramMessage

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def check_db_connection():
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    if not DATABASE_ENABLED:
        return False

    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
