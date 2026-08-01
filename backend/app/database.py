"""
SQLAlchemy async engine and session setup.
Uses SQLite via aiosqlite driver. DB file at backend/data/app.db,
created automatically on first run. See Plan.md §12.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Ensure the data directory exists so SQLite can create the file
_db_dir = Path(__file__).resolve().parent.parent / "data"
_db_dir.mkdir(parents=True, exist_ok=True)

# Build the absolute database URL
_db_path = _db_dir / "app.db"
DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # required for SQLite
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async DB session."""
    async with async_session_maker() as session:
        yield session


async def create_tables() -> None:
    """Create all tables from ORM metadata. Called on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
