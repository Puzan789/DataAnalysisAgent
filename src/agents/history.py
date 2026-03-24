from langchain_core.messages import HumanMessage, AIMessage, trim_messages as trim_msgs
from langgraph.graph.message import add_messages


def trim_messages_reducer(
    existing: list[HumanMessage | AIMessage], new: list[HumanMessage | AIMessage]
) -> list[HumanMessage | AIMessage]:
    """Add messages (with deduplication) and automatically trim."""

    merged = add_messages(existing, new)

    return trim_msgs(
        merged,
        strategy="last",
        token_counter=len,
        max_tokens=8,
        start_on="human",
        include_system=True,
    )
