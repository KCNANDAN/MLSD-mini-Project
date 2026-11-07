from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import get_settings


settings = get_settings()

# Ensure the local storage directory exists for SQLite.
Path("storage").mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""
    pass


connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    """Provide a database session and always close it."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def initialize_database():
    """Create all registered database tables."""

    # Import models so SQLAlchemy registers their table metadata.
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)