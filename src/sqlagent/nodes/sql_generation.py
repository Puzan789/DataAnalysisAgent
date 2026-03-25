from langgraph.prebuilt import create_react_agent
from jinja2 import Template
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import datetime
from loguru import logger
from src.tools.sql_execution_tool import sql_tool
from src.prompts import SQL_GENERATION_SYSTEM_PROMPT, SQL_GENERATION_USER_PROMPT_TEMPLATE

from src.core.utils import get_llm
llm=get_llm()


async def sql_generation_node(state: dict):
    tools = [sql_tool]
    template = Template(SQL_GENERATION_USER_PROMPT_TEMPLATE)

    # Check if retrieval_results exist, if not, retrieve them
    retrieval_output = state.get("retrieval_results", {})
    if not retrieval_output or not retrieval_output.get("retrieval_results"):
        # Retrieval results not found, perform retrieval now
        from src.sqlagent.retrieval import Retriever

        retriever = Retriever()
        query = state.get("query", "")
        logger.info(
            f"[SQL Generation Node] No retrieval results found, retrieving for query: {query}"
        )
        retrieval_output = retriever.retriever(query=query)
        state["retrieval_results"] = retrieval_output
        logger.info(
            f"[SQL Generation Node] Retrieved {len(retrieval_output.get('retrieval_results', []))} schemas"
        )

    retrieval_results = retrieval_output.get("retrieval_results", [])
    documents = [result["table_ddl"] for result in retrieval_results]

    # Extract validator feedback for retry attempts
    sql_generation_reasoning = ""
    validator_result = (
        state.get("agent_outputs", {}).get("sql_validator", {}).get("result", {})
    )
    if validator_result:
        if hasattr(validator_result, "reasoning") and validator_result.reasoning:
            sql_generation_reasoning = f"Previous attempt was rejected. Feedback: {validator_result.reasoning}"
        elif isinstance(validator_result, dict) and validator_result.get("reasoning"):
            sql_generation_reasoning = f"Previous attempt was rejected. Feedback: {validator_result['reasoning']}"

    rendered_prompt = template.render(
        documents=documents,
        sql_samples=state.get("sql_samples", []),
        sql_functions=state.get("sql_functions", []),
        instructions=state.get("instructions", []),
        query=state.get("query", ""),
        language=state.get("language", "English"),
        current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sql_generation_reasoning=sql_generation_reasoning,
    )
    messages = [
        SystemMessage(content=SQL_GENERATION_SYSTEM_PROMPT),
        *state.get("messages", []),
        HumanMessage(content=rendered_prompt),
    ]
    # Create react_agent without checkpointer to avoid async issues
    react_agent = create_react_agent(llm, tools, checkpointer=None)

    response = await react_agent.ainvoke({"messages": messages})
    sql_queries = []
    for msg in response.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                tool_args = call.get("args")
                sql_generated = tool_args["query"]
                sql_queries.append(sql_generated)
                logger.info(f"[SQL Generation Node] Generated SQL: {sql_generated}")

    generated_sql = sql_queries[0] if sql_queries else ""

    # If no SQL was generated, extract the LLM's direct text response
    if not generated_sql:
        for msg in reversed(response.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                state["llm_response"] = msg.content
                break

    logger.info(f"[SQL Generation Node] Final generated SQL: {generated_sql}")

    state["generated_sql"] = generated_sql
    state["current_agent"] = "sql_generation_node"
    return state
