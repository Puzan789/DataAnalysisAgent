from __future__ import annotations
from dataclasses import dataclass
from src.database.postgres import PostgresConnection
from src.database.mongo import MongoConnection
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver


@dataclass
class DatabaseState:
    """Container for all the databases connections."""

    postgres: PostgresConnection
    mongo: MongoConnection
    checkpointer: AsyncMongoDBSaver

    async def connect_all(self):
        """Connect to all the databases."""
        await self.postgres.connect()
        await self.mongo.connect()

    async def disconnect_all(self):
        """Disconnect from all the databases."""
        await self.postgres.disconnect()
        await self.mongo.disconnect()

    async def health_check(self) -> dict[str, bool]:
        """Check health of all connections."""
        return {
            "postgres": await self.postgres.health_check(),
            "mongo": await self.mongo.health_check(),
        }


def create_database_state(settings) -> DatabaseState:
    """Factory function to create DatabaseState instance."""
    from src.database.models import (
        Message,
        Session,
        User,
    )

    postgres_conn = PostgresConnection(settings=settings)
    mongo_conn = MongoConnection(
        settings=settings, document_models=[Message, Session, User]
    )
    return DatabaseState(
        postgres=postgres_conn,
        mongo=mongo_conn,
        checkpointer=None,  # Can't create checkpointer until mongo is connected, so we'll do it in the lifespan
    )


_global_db_state: DatabaseState | None = None


def set_global_db_state(db_state: DatabaseState):
    """Set global database state (called from main.py)."""
    global _global_db_state
    _global_db_state = db_state


def get_global_db_state() -> DatabaseState:
    """Get global database state for agents."""
    if _global_db_state is None:
        raise RuntimeError("Database not initialized")
    return _global_db_state
