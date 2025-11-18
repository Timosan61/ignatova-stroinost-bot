"""
Database configuration and session management.
Supports both MySQL (Railway) and PostgreSQL (Vercel) with serverless-optimized pooling.
Adapted from GPTIFOBIZ architecture for Ignatova-Stroinost bot.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger
logger = logging.getLogger(__name__)

# Detect environment: Vercel (serverless) or Railway (persistent)
IS_VERCEL = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None

# Database URL from environment
# Vercel provides POSTGRES_URL, Railway provides DATABASE_URL (MySQL)
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("No database URL found (POSTGRES_URL or DATABASE_URL). Database features will be disabled.")
    DATABASE_ENABLED = False
    DATABASE_TYPE = None
    engine = None
    SessionLocal = None
    Base = declarative_base()
else:
    DATABASE_ENABLED = True

    # Detect database type from URL
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        DATABASE_TYPE = "PostgreSQL"
    elif DATABASE_URL.startswith("mysql"):
        DATABASE_TYPE = "MySQL"
    else:
        DATABASE_TYPE = "Unknown"

    # Serverless-optimized configuration for Vercel
    if IS_VERCEL:
        logger.info("🚀 Detected Vercel serverless environment - using NullPool for database connections")

        # NullPool: No connection pooling (создает новое соединение при каждом запросе)
        # Ideal for serverless functions где контейнер может быть остановлен в любой момент
        engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,  # No pooling for serverless
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL query logging
        )
    else:
        # Traditional connection pooling для persistent environments (Railway)
        logger.info("🔧 Detected persistent environment - using QueuePool for database connections")

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

    # Log database info (hide credentials)
    db_host = DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'localhost'
    logger.info(f"✅ Database engine created successfully: {DATABASE_TYPE} @ {db_host}")
    if IS_VERCEL:
        logger.info("⚡ Serverless mode: NullPool (new connection per request)")
    else:
        logger.info("🔄 Persistent mode: QueuePool (connection pooling enabled)")


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
        from bot.database.models import TelegramChat, TelegramMessage, GraphitiCheckpoint

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (including graphiti_checkpoint)")

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
