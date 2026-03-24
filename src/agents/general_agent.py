import traceback
from typing import Any
from loguru import logger
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith import traceable
from src.sqlagent.nodes import sql_generation_node, execute_sql_node
from src.prompts import get_general_agent_prompt


class GeneralAgent:
    """An agent that handles general user questions using SQL-based QnA."""

    def __init__(self, llm):
        if llm is None:
            raise ValueError("LLM must be provided")
        self.llm = llm

    @traceable
    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        updated_state = state.copy()
        messages = state.get("messages", [])

        user_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break
            elif hasattr(msg, "type") and msg.type == "human":
                user_query = msg.content
                break
        user_query = user_query or state.get("query", "") or ""

        logger.info(f"[GeneralAgent] Processing user query: {user_query}")
        updated_state["current_agent"] = "general_agent"

        if "agent_outputs" not in updated_state:
            updated_state["agent_outputs"] = {}

        try:
            workflow_state = {
                "query": user_query,
                "messages": messages,
                "language": "English",
                "agent_outputs": state.get("agent_outputs", {}),
            }

            logger.info("[GeneralAgent] Step 1/2: SQL Generation")
            workflow_state = await sql_generation_node(workflow_state)
            generated_sql = workflow_state.get("generated_sql", "")
            logger.info(f"[GeneralAgent] Generated SQL: {generated_sql}")

            if not generated_sql:
                direct_answer = workflow_state.get("llm_response", "")
                if not direct_answer:
                    direct_answer = "I can help you query the database. Please ask a specific question about the data."
                updated_state["messages"] = [AIMessage(content=direct_answer)]
                return updated_state

            logger.info("[GeneralAgent] Step 2/2: SQL Execution")
            workflow_state = await execute_sql_node(workflow_state)
            sql_results = workflow_state.get("sql_results", {})

            if sql_results.get("success"):
                results_data = sql_results.get("results", [])
                answer_prompt = get_general_agent_prompt(
                    user_query=user_query,
                    generated_sql=generated_sql,
                    sql_results=results_data,
                )
                answer_messages = [
                    SystemMessage(content=answer_prompt),
                ]
                answer_result = self.llm.invoke(answer_messages)
                if hasattr(answer_result, "content"):
                    result = answer_result.content
                else:
                    result = str(answer_result)
            else:
                error_msg = sql_results.get("error", "No results found")
                result = f"I couldn't find relevant data for your question. Error: {error_msg}"

            updated_state["messages"] = [AIMessage(content=result)]
            return updated_state

        except Exception as e:
            traceback.print_exc()
            logger.error(f"[GeneralAgent] Error processing user query: {e}")
            updated_state["messages"] = [
                AIMessage(
                    content="I'm sorry, but I couldn't process your request at this time."
                ),
            ]
            return updated_state
