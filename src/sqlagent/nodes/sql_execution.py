from sqlalchemy import text
from loguru import logger


async def execute_sql_with_async(query: str) -> dict:
    """Execute SQL query using the async db_state session."""
    try:
        from src.database.state import get_global_db_state

        db_state = get_global_db_state()
        async with db_state.postgres.get_session() as session:
            result = await session.execute(text(query))

            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(row._mapping) for row in result]
                return {
                    "success": True,
                    "results": rows,
                    "row_count": len(rows),
                    "columns": columns,
                }
            else:
                return {
                    "success": True,
                    "message": "Query executed successfully",
                    "rows_affected": result.rowcount,
                }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def execute_sql_node(state: dict):
    """Node to execute SQL query"""

    generated_sql = state.get("generated_sql", "")

    if not generated_sql:
        if "agent_outputs" not in state:
            state["agent_outputs"] = {}
        if "sql_agents" not in state["agent_outputs"]:
            state["agent_outputs"]["sql_agents"] = {}
        state["agent_outputs"]["sql_agents"] = {
            "status": "error",
            "result": [],
            "sql": [],
            "step": 0,
        }
        return state

    # Execute SQL
    logger.info(f"[SQL Execution Node] Executing SQL: {generated_sql}")
    results = await execute_sql_with_async(generated_sql)
    logger.info(f"[SQL Execution Node] SQL Results: {results}")
    state["sql_results"] = results
    if "agent_outputs" not in state:
        state["agent_outputs"] = {}
    if "sql_agents" not in state["agent_outputs"]:
        state["agent_outputs"]["sql_agents"] = {}

    current_step = (
        state.get("agent_outputs", {}).get("sql_agents", {}).get("step", 0)
    )

    if results.get("success"):
        state["agent_outputs"]["sql_agents"] = {
            "status": "completed",
            "result": results,
            "sql": [generated_sql] if isinstance(generated_sql, str) else generated_sql,
            "step": current_step + 1,
        }
        logger.info(
            f"[SQL Execution Node] Step {current_step + 1}: Retrieved {results.get('row_count', 0)} rows"
        )
    else:
        error_msg = results.get("error", "Unknown error")
        state["agent_outputs"]["sql_agents"] = {
            "status": "error",
            "result": results,
            "sql": [generated_sql] if isinstance(generated_sql, str) else generated_sql,
            "step": current_step + 1,
        }
        logger.error(f"[SQL Execution Node] SQL execution failed: {error_msg}")

    state["current_agent"] = "sql_execution_node"
    state["next_agent"] = "validate_results"

    return state
