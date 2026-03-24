from contextlib import asynccontextmanager
from loguru import logger
from src.config import Settings
from src.database.base import DatabaseConnection, SessionProvider
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy import text



class PostgresConnection(DatabaseConnection, SessionProvider):
    """PostgreSQL database connection and session provider."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    async def connect(self):
        """Establish the database connection."""
        db_url = self._build_connection_url()
        self._engine = create_async_engine(db_url)
        self._session_maker = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("PostgreSQL database engine created successfully.")

    async def disconnect(self):
        """Close database connection at shutdown."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgreSQL database connection closed.")

    async def health_check(self) -> bool:
        """Check PostgreSQL connection health."""
        if not self._engine:
            return False
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    def _build_connection_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self._settings.POSTGRES_USERNAME}:"
            f"{self._settings.POSTGRES_PASSWORD}@{self._settings.POSTGRES_HOST}:"
            f"{self._settings.POSTGRES_PORT}/{self._settings.POSTGRES_DB}"
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Get postgres Sql session for each request."""
        if not self._session_maker:
            raise Exception(
                "Database not initialized. PostgreSQL configuration may be missing."
            )
        async with self._session_maker() as session:
            yield session

    # this is for using the session outside the depends
    @property
    def session_maker(self):
        """Expose session maker for agents ."""
        if not self._session_maker:
            raise RuntimeError(
                "Database not initialized. PostgreSQL configuration may be missing."
            )
        return self._session_maker
