from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Any
from datetime import datetime
from src.prompts import get_router_prompt
import json
import re
import ast
from langsmith import traceable
import traceback
from src.schemas.llm_response_schemas import RouterResponse
from langchain_core.output_parsers import JsonOutputParser

CURRENT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_llm_output(response_str: str):
    """
    Try to parse an LLM string output into Python dict/list/etc.
    Tries multiple methods: json, ast.literal_eval, regex cleanup.
    """
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(response_str)
        except (ValueError, SyntaxError):
            try:
                match = re.search(r"\{.*\}", response_str, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


class RoutingAgent:
    def __init__(self, llm):
        if llm is None:
            raise ValueError("LLM must be provided")
        self.llm = llm

    @traceable
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Invoke the routing agent with the given state.
        Args:
            state: A dictionary containing the current state or context for the agent.

        Returns:
            Updated state after determining the appropriate agent to handle the user query.
        """
        updated_state = state.copy()
        query = state.get("query", "")
        messages = state.get("messages", [])
        if not query and state.get("messages"):
            # Extract the last user message from the messages
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    query = msg.content
                    break
                elif hasattr(msg, "type") and msg.type == "human":
                    query = msg.content
                    break
        query = query or " "
        updated_state["current_agent"] = "router"
        if "agent_outputs" not in updated_state:
            updated_state["agent_outputs"] = {}
        try:
            parser = JsonOutputParser(pydantic_object=RouterResponse)
            router_prompt = get_router_prompt(format_instructions=parser.get_format_instructions())
            # trimmed_messages = trim(state.get("messages"))
            logger.info(f"The trimmed messages is {messages}")
            messages = [SystemMessage(content=router_prompt)] + messages
            
            router_llm = self.llm.with_structured_output(RouterResponse)
            llm_results = router_llm.invoke(messages)


            updated_state["agent_outputs"]["router"] = llm_results.route_to
            updated_state["next_agent"] = llm_results.route_to

            logger.info(
                f"[RoutingAgent] Routing to agent: {updated_state['next_agent']}"
            )

            return updated_state

        # TODO: To return the error in the form of the result directly to the user like result:Error handling the request for now type of messages.
        except Exception as e:
            logger.error(f"[RoutingAgent] Error determining next agent: {e}")
            traceback.print_exc()
            updated_state["next_agent"] = "general_agent"
            updated_state["agent_outputs"]["router"] = {
                "route_to": "general_agent",
                "status": "error",
                "result": f"Error: {e}",
            }

            return updated_state
