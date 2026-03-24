import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel

from loguru import logger
from src.core.exception import CustomException, NotFoundException
from src.core.responses import APIResponse
from langfuse.langchain import CallbackHandler
from src.database.dependencies import get_checkpointer
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from fastapi import Depends


from src.services.message_service import (
    delete_session,
    get_threads_of_a_user,
    get_messages_thread,
    deactivate_session,
)

router = APIRouter()
langfuse_handler = CallbackHandler()


class QueryRequest(BaseModel):
    query: str
    chat_id: uuid.UUID
    user_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000123")  # fixed UUID


run_configs = {}


@router.delete("/delete_thread/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_thread(
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    checkpointer: AsyncMongoDBSaver = Depends(get_checkpointer),
):
    """
    Delete a chat thread and all associated messages.
    """
    try:
        response = await delete_session(user_id, thread_id, checkpointer)
        if response:
            return APIResponse(success=True, message=response["message"])
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error while deleting thread: {str(e)}")
        raise CustomException(message="Error while deleting thread.")


@router.get("/threads/{user_id}", status_code=status.HTTP_200_OK)
async def get_threads_for_user(user_id: uuid.UUID):
    """
    Retrieve all chat threads for a specific user.
    """
    try:
        threads = await get_threads_of_a_user(user_id)
        return APIResponse(
            success=True, message="Threads retrieved successfully", data=threads
        )
    except NotFoundException:
        raise

    except Exception as e:
        logger.error(f"Error retrieving threads: {str(e)}")
        raise CustomException(message="Error retrieving threads") from e


@router.get("/messages/{thread_id}", status_code=status.HTTP_200_OK)
async def get_messages_for_thread(thread_id: uuid.UUID, user_id: uuid.UUID):
    """
    Retrieve all messages in a specific chat thread.
    """
    try:
        response = await get_messages_thread(user_id=user_id, thread_id=thread_id)
        return APIResponse(
            success=True, message="Messages retrieved for the thread", data=response
        )
    except NotFoundException:
        raise

    except Exception as e:
        logger.error(f"Error retrieving messages for the thread: {str(e)}")
        raise CustomException(
            message="Error retrieving messages for the thread."
        ) from e


@router.put("/{thread_id}/deactivate")
async def deactivate_session_endpoint(thread_id: uuid.UUID):
    try:
        response = await deactivate_session(thread_id)
        return APIResponse(success=True, message=response["message"])
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating the session: {str(e)}")
        raise CustomException(message="Error deactivating the session") from e
