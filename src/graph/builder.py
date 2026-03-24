from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from typing import Annotated, Any, TypedDict
from src.agents import RoutingAgent, GeneralAgent, SqlAgent
from src.core.utils import get_llm
from src.agents.history import trim_messages_reducer

llm = get_llm()


class GraphState(TypedDict):
    query: str
    messages: Annotated[list[HumanMessage | AIMessage], trim_messages_reducer]
    current_agent: str
    agent_outputs: dict[str, Any]
    next_agent: str


async def build_agent_graph(checkpointer):
    """Builds the agent graph for handling user queries."""
    workflow = StateGraph(GraphState)
    router_agent = RoutingAgent(llm)
    general_agent = GeneralAgent(llm)
    sql_agent = SqlAgent(llm)

    workflow.add_node("router", router_agent.invoke)
    workflow.add_node("general_agent", general_agent.invoke)
    workflow.add_node("sql_agents", sql_agent.invoke)
    workflow.add_node("validate_results", sql_agent.validate_results)
    workflow.add_node("generate_response", sql_agent.generate_response)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        lambda x: x.get("next_agent", "general_agent"),
        {
            "general_agent": "general_agent",
            "sql_agents": "sql_agents",
        },
    )
    workflow.add_edge("general_agent", END)
    workflow.add_edge("sql_agents", "validate_results")
    workflow.add_conditional_edges(
        "validate_results",
        sql_agent.decide_next,
        {
            "generate_response": "generate_response",
            "sql_agents": "sql_agents",
        },
    )
    workflow.add_edge("generate_response", END)

    return workflow.compile(checkpointer=checkpointer)
