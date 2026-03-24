import uuid
from fastapi import APIRouter, Request, status, BackgroundTasks, Depends
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessageChunk
import json
from sse_starlette.sse import EventSourceResponse
from langsmith import traceable
from loguru import logger
from src.core.exception import CustomException, NotFoundException
from src.core.responses import APIResponse
from langfuse.langchain import CallbackHandler
from src.database.dependencies import get_checkpointer
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver


from src.services.message_service import (
    create_session,
    add_message_separately,
    delete_session,
    get_threads_of_a_user,
    get_messages_thread,
    deactivate_session,
)
from src.api.v1.auth import get_current_user
from src.database.models import User

router = APIRouter()
langfuse_handler = CallbackHandler()


class QueryRequest(BaseModel):
    query: str
    chat_id: uuid.UUID




async def save_messages_background(user_id, thread_id, message, role):
    session = await create_session(thread_id, user_id)
    await add_message_separately(session, message, role)


@traceable
@router.post("/graph/stream/graph")
async def create_graph_streaming(
    request: QueryRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    graph = req.app.state.services.graph

    thread_id = request.chat_id
    config = {"configurable": {"thread_id": thread_id}, "callbacks": [langfuse_handler]}
    initial_state = {
        "query": request.query,
        "messages": [HumanMessage(content=request.query)],
    }

    async def event_generator():
        events_list = []
        full_response = ""

        async for event in graph.astream_events(initial_state, config, version="v2"):
            if await req.is_disconnected():
                break
            events_list.append(event)
            if (
                event["event"] == "on_chain_end"
                and event.get("name") == "decide_next"
                and event.get("metadata", {}).get("langgraph_node")
                == "validate_results"
            ):
                data = event.get("data", {})
                input_data = data.get("input", {})

                logger.info(f"Data: {data}")

                # Extract approved IDs from input
                approved_ids = input_data.get("approved_ids")

                if approved_ids:
                    logger.info(f"Streaming approved package IDs: {approved_ids}")
                    yield {
                        "event": "ids",
                        "data": json.dumps({"ids": approved_ids}),
                    }

            elif event["event"] == "on_chat_model_stream":
                metadata = event.get("metadata", {})
                node = metadata.get("langgraph_node")
                checkpoint_ns = metadata.get("langgraph_checkpoint_ns", "")
                node_agents = ["general_agent", "generate_response"]
                checkpoint_ns_agents = []
                if node in node_agents or any(
                    agent in checkpoint_ns for agent in checkpoint_ns_agents
                ):
                    message = event["data"].get("chunk")
                    if isinstance(message, AIMessageChunk) and hasattr(
                        message, "content"
                    ):
                        token_data = json.dumps({"content": message.content})
                        full_response += message.content
                        yield {"event": "token", "data": token_data}

        background_tasks.add_task(
            save_messages_background, current_user.id, thread_id, request.query, "user"
        )
        background_tasks.add_task(
            save_messages_background,
            current_user.id,
            thread_id,
            full_response,
            "assistant",
        )

    return EventSourceResponse(event_generator())


@router.delete("/delete_thread/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_thread(
    thread_id: uuid.UUID,
    checkpointer: AsyncMongoDBSaver = Depends(get_checkpointer),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a chat thread and all associated messages.
    """
    try:
        response = await delete_session(current_user.id, thread_id, checkpointer)
        if response:
            return APIResponse(success=True, message=response["message"])
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error while deleting thread: {str(e)}")
        raise CustomException(message="Error while deleting thread.")


@router.get("/threads/{user_id}", status_code=status.HTTP_200_OK)
async def get_threads_for_user(
    user_id: uuid.UUID, current_user: User = Depends(get_current_user)
):
    """
    Retrieve all chat threads for a specific user.
    """
    try:
        if current_user.id != user_id:
            raise CustomException(
                message="Forbidden", status_code=status.HTTP_403_FORBIDDEN
            )
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
async def get_messages_for_thread(
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all messages in a specific chat thread.
    """
    try:
        if current_user.id != user_id:
            raise CustomException(
                message="Forbidden", status_code=status.HTTP_403_FORBIDDEN
            )
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
async def deactivate_session_endpoint(
    thread_id: uuid.UUID, current_user: User = Depends(get_current_user)
):
    try:
        response = await deactivate_session(thread_id)
        return APIResponse(success=True, message=response["message"])
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating the session: {str(e)}")
        raise CustomException(message="Error deactivating the session") from e
