from langgraph.graph import MessagesState
from typing import TypedDict


class RecommendationState(TypedDict):
    filters: str | None = None
    criteria: str | None = None


class State(MessagesState):
    query: str
    recommendation: RecommendationState | None = None
    agent_output: dict[str, any]
    current_agent: str | None = None
    next_agent: str | None = None
