"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config import config


# Create async engine
if config.database_url.startswith("sqlite"):
    # SQLite needs special handling for async
    engine = create_async_engine(
        config.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=config.env == "dev",
    )
else:
    # For PostgreSQL, MySQL, etc.
    engine = create_async_engine(
        config.database_url,
        echo=config.env == "dev",
    )

# Create async session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency for getting async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database and create tables."""
    from models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()