from __future__ import annotations
from loguru import logger
from pymongo import AsyncMongoClient
from beanie import init_beanie
from src.config import Settings
from src.database.base import DatabaseConnection


class MongoConnection(DatabaseConnection):
    """MongoDB database connection."""

    def __init__(self, settings: Settings, document_models: list):
        self._settings = settings
        self._document_models = document_models
        self._client: AsyncMongoClient | None = None

    async def connect(self):
        """Initialize MongoDB connection."""
        self._client = AsyncMongoClient(
            self._settings.MONGO_DB_URI
        )  # NOTE: Add(maxpoolsize,minpoolsize,serverselectiontimeout)

        # Verify connection
        await self._client.admin.command("ping")

        database = self._client[self._settings.MONGO_DB_NAME]
        await init_beanie(database, document_models=self._document_models)
        logger.info(f"MongoDB connected: {self._settings.MONGO_DB_NAME}")

    async def disconnect(self) -> None:
        """Close MongoDb connection"""
        if self._client:
            await self._client.close()
            logger.info("MongoDB connection closed.")

    async def health_check(self) -> bool:
        """Check MongoDB connection health."""
        if not self._client:
            return False

        try:
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    def get_client(self) -> AsyncMongoClient:
        """Get MongoDB client instance."""
        if not self._client:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._client
