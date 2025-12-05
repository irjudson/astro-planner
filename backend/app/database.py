"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Get database URL from environment or use default
DATABASE_URL = settings.database_url
print(f"DATABASE_URL: {DATABASE_URL}")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True for SQL logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test engine for test database
TEST_DATABASE_URL = settings.test_database_url
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}, echo=False
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_test_db():
    """Get a transactional database session for testing."""
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestSessionLocal(bind=connection)
    try:
        yield db
    finally:
        transaction.rollback()
        connection.close()


def init_db():
    """Initialize database (create all tables)."""
    Base.metadata.create_all(bind=engine)
