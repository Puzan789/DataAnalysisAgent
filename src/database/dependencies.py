from fastapi import Depends, Request
from src.database.state import DatabaseState
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from pymongo import AsyncMongoClient


def get_db_state(request: Request):
    """Return objects from app.state"""
    return request.app.state.db


async def get_postgres_session(
    db_state: DatabaseState = Depends(get_db_state),
) -> AsyncGenerator[AsyncSession, None]:
    """Get postgres SQL session for main database (packages, destinations, etc.)."""
    async with db_state.postgres.get_session() as session:
        yield session


def get_mongo_client(
    db_state: DatabaseState = Depends(get_db_state),
) -> AsyncMongoClient:
    """Returns object of mongo_client"""
    return db_state.mongo.get_client()


def get_checkpointer(
    db_state: DatabaseState = Depends(get_db_state),
) -> AsyncMongoDBSaver:
    """Just returns object"""
    return db_state.checkpointer
