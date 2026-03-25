from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.prompts._prompts import get_generation_prompt, get_validation_prompt
from loguru import logger
import json
import traceback
from langsmith import traceable
from langchain_core.output_parsers import JsonOutputParser
from src.schemas.llm_response_schemas import EvaluationResponse
from src.sqlagent.nodes import sql_generation_node, execute_sql_node


class SqlAgent:
    """
    Agent that uses the 2-node SQL workflow:
    1. sql_generation_node - generates SQL (with automatic schema retrieval via vector DB)
    2. execute_sql_node - executes SQL and formats results
    """

    def __init__(self, llm):
        if llm is None:
            raise ValueError("LLM must be provided")
        self.llm = llm

    @traceable
    async def invoke(self, state: dict):
        """Main node - executes the 2-node SQL workflow"""
        updated_state = state.copy()
        messages = state.get("messages", [])

        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
            elif hasattr(msg, "type") and msg.type == "human":
                query = msg.content
                break
        query = query or ""

        updated_state["current_agent"] = "sql_agent"
        if "agent_outputs" not in updated_state:
            updated_state["agent_outputs"] = {}
        if "sql_agents" not in updated_state["agent_outputs"]:
            updated_state["agent_outputs"]["sql_agents"] = {}

        sql_steps = state.get("agent_outputs", {}).get("sql_agents", {}).get("step", 0)
        logger.info(f"[SqlAgent] Steps: {sql_steps}")

        try:
            workflow_state = {
                "query": query,
                "messages": messages,
                "language": "English",
                "agent_outputs": state.get("agent_outputs", {}),
            }

            if sql_steps >= 1:
                eval_results = (
                    state.get("agent_outputs", {})
                    .get("sql_validator", {})
                    .get("result", {})
                )
                workflow_state["agent_outputs"]["sql_validator"] = {
                    "result": eval_results
                }

            logger.info("[SqlAgent] Step 1/2: SQL Generation")
            workflow_state = await sql_generation_node(workflow_state)
            generated_sql = workflow_state.get("generated_sql", "")
            logger.info(f"[SqlAgent] Generated SQL: {generated_sql}")

            logger.info("[SqlAgent] Step 2/2: SQL Execution")
            workflow_state = await execute_sql_node(workflow_state)
            sql_results = workflow_state.get("sql_results", {})

        
            updated_step = sql_steps + 1


            if sql_results.get("success") and sql_results.get("results"):
                updated_state["agent_outputs"]["sql_agents"] = {
                    "status": "completed",
                    "result": sql_results,
                    "sql": [generated_sql]
                    if isinstance(generated_sql, str)
                    else generated_sql,
                    "step": updated_step,
                }
            
            else:
                error_msg = sql_results.get("error", "Unknown error")
                updated_state["agent_outputs"]["sql_agents"] = {
                    "status": "error",
                    "result": sql_results,
                    "sql": [generated_sql]
                    if isinstance(generated_sql, str)
                    else generated_sql,
                    "step": updated_step,
                }
                logger.error(
                    f"[SqlAgent] Step {updated_step}: SQL execution failed: {error_msg}"
                )

            updated_state["next_agent"] = "validate_results"
            return updated_state

        except Exception as e:
            logger.error(f"[SqlAgent] Error: {e}")
            traceback.print_exc()
            updated_state["agent_outputs"]["sql_agents"] = {
                "status": "error",
                "result": {"error": str(e)},
                "sql": [],
                "step": sql_steps + 1,
            }
            updated_state["next_agent"] = "validate_results"
            return updated_state

    async def validate_results(self, state):
        """Validates the SQL results and decides whether to retry or proceed"""
        updated_state = state.copy()
        messages = state.get("messages", [])

        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
            elif hasattr(msg, "type") and msg.type == "human":
                query = msg.content
                break
        query = query or " "

        sql_results = (
            state.get("agent_outputs", {}).get("sql_agents", {}).get("result", {})
        )
        sql = state.get("agent_outputs", {}).get("sql_agents", {}).get("sql", [])


        parser = JsonOutputParser(pydantic_object=EvaluationResponse)
        try:
            evaluation_prompt = get_validation_prompt(
                user_query=query,
                sql=sql,
                tool_results=sql_results,
                format_instructions=parser.get_format_instructions(),
            )

            eval_messages = [
                SystemMessage(content=evaluation_prompt),
                HumanMessage(content=query),
            ]

            evaluation_llm = self.llm.with_structured_output(EvaluationResponse)
            result = await evaluation_llm.ainvoke(eval_messages)

            logger.info(f"[SqlValidator] Results: {result}")

    

            updated_state["agent_outputs"]["sql_validator"] = {
                "status": "completed",
                "result": result,
            }
            return updated_state

        except Exception as e:
            traceback.print_exc()
            logger.error(f"[SqlValidator] Error validating results: {e}")
            updated_state["agent_outputs"]["sql_validator"] = {
                "status": "error",
                "result": "Error during validation.",
            }
            return updated_state

    def decide_next(self, state):
        """Decides whether to retry or proceed to response generation"""
        eval_results = (
            state.get("agent_outputs", {}).get("sql_validator", {}).get("result", {})
        )
        sql_steps = state.get("agent_outputs", {}).get("sql_agents", {}).get("step", 0)
        logger.info(f"[SqlDecider] Validation results: {eval_results}")

        if sql_steps > 2:
            logger.warning(f"[SqlDecider] Step {sql_steps} reached max retries.")
            return "generate_response"

        if isinstance(eval_results, str):
            try:
                eval_results = json.loads(eval_results)
            except json.JSONDecodeError:
                return "generate_response"

        if hasattr(eval_results, "approval"):
            return "generate_response" if eval_results.approval else "sql_agents"

        return "generate_response"

    @traceable
    async def generate_response(self, state):
        """Generates user-friendly response from the results"""
        updated_state = state.copy()

        sql_results = (
            state.get("agent_outputs", {}).get("sql_agents", {}).get("result", {})
        )

        query = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
            elif hasattr(msg, "type") and msg.type == "human":
                query = msg.content
                break

        try:
            generation_prompt = get_generation_prompt(results=sql_results, query=query)
            desc_messages = [
                SystemMessage(content=generation_prompt),
                HumanMessage(content=query),
            ]

            gen_result = await self.llm.ainvoke(desc_messages)
            if hasattr(gen_result, "content"):
                result = gen_result.content
            else:
                result = str(gen_result)

            updated_state["messages"] = [AIMessage(content=result)]
            updated_state["agent_outputs"] = {}
            return updated_state

        except Exception as e:
            traceback.print_exc()
            logger.error(f"[SqlAgent] Error generating response: {e}")
            updated_state["messages"] = [
                AIMessage(
                    content="I'm sorry, but I couldn't process your request at this time."
                ),
            ]
            return updated_state
