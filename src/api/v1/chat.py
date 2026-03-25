import uuid
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessageChunk
import json
from sse_starlette.sse import EventSourceResponse
from langsmith import traceable
from loguru import logger
from langfuse.langchain import CallbackHandler

from src.services.message_service import (
    create_session,
    add_message_separately,
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
        full_response = ""
        emitted_steps = set()

        def step_event(step_type: str, label: str, detail: str = ""):
            """Helper to create a step SSE event."""
            return {
                "event": "step",
                "data": json.dumps(
                    {"type": step_type, "label": label, "detail": detail}
                ),
            }

        async for event in graph.astream_events(initial_state, config, version="v2"):
            if await req.is_disconnected():
                break

            event_type = event["event"]
            metadata = event.get("metadata", {})
            node = metadata.get("langgraph_node", "")
            data = event.get("data", {})

            # Emit step events on node start
            if event_type == "on_chain_start":
                step_key = f"{node}_{event.get('name', '')}"
                if step_key in emitted_steps:
                    continue
                emitted_steps.add(step_key)

                if node == "router" and event.get("name") == "router":
                    yield step_event("routing", "Analyzing your question...")
                elif node == "sql_agents" and event.get("name") == "sql_agents":
                    yield step_event("sql_agent", "SQL Agent started")
                elif node == "general_agent" and event.get("name") == "general_agent":
                    yield step_event(
                        "general_agent", "Processing with General Agent..."
                    )
                elif (
                    node == "validate_results"
                    and event.get("name") == "validate_results"
                ):
                    yield step_event("validating", "Validating SQL results...")
                elif (
                    node == "generate_response"
                    and event.get("name") == "generate_response"
                ):
                    yield step_event("generating", "Generating response...")

            # Emit step when routing decision is made
            elif event_type == "on_chain_end" and node == "router":
                output = data.get("output", {})
                next_agent = (
                    output.get("next_agent", "") if isinstance(output, dict) else ""
                )
                if next_agent:
                    agent_label = (
                        "SQL Agent" if next_agent == "sql_agents" else "General Agent"
                    )
                    yield step_event("routed", f"Routed to {agent_label}")

            # Capture SQL generation details from agent outputs
            elif event_type == "on_chain_end" and node in (
                "sql_agents",
                "general_agent",
            ):
                output = data.get("output", {})
                if isinstance(output, dict):
                    agent_data = output.get("agent_outputs", {}).get("sql_agents", {})
                    sql_list = agent_data.get("sql", [])
                    if sql_list:
                        sql_str = (
                            sql_list[0] if isinstance(sql_list, list) else str(sql_list)
                        )
                        yield step_event("sql_generated", "Generated SQL", sql_str)

                    result = agent_data.get("result", {})
                    if isinstance(result, dict):
                        row_count = len(result.get("results", []))
                        if result.get("success"):
                            yield step_event(
                                "sql_executed", f"Query returned {row_count} rows"
                            )
                            # Emit chart_data event so frontend can trigger chart generation
                            yield {
                                "event": "chart_data",
                                "data": json.dumps({
                                    "sql": sql_str if sql_list else "",
                                    "query": request.query,
                                    "data": result,
                                }),
                            }
                        elif result.get("error"):
                            yield step_event(
                                "sql_error", "SQL execution error", result["error"]
                            )

            # Stream response tokens
            elif event_type == "on_chat_model_stream":
                response_nodes = ["general_agent", "generate_response"]
                if node in response_nodes:
                    message = data.get("chunk")
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
