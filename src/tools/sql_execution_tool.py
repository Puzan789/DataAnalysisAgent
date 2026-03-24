from langchain_core.tools import StructuredTool
from src.schemas.tool_input_schemas import SQLQueryInput


async def execute_sql_query(query: str) -> dict:
    """Executes SQL query and returns structured results with column names."""
    try:
        from sqlalchemy import text
        from src.database.state import get_global_db_state

        db_state = get_global_db_state()
        async with db_state.postgres.get_session() as session:
            cursor_result = await session.execute(text(query))
            columns = list(cursor_result.keys())
            rows_raw = cursor_result.fetchall()

            if not rows_raw:
                return {
                    "rows": [],
                    "columns": columns,
                    "count": 0,
                    "message": "No results found matching your criteria.",
                }

            rows = []
            for row in rows_raw:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    row_dict[col_name] = row[i]
                rows.append(row_dict)

            return {
                "rows": rows,
                "count": len(rows),
                "columns": columns,
            }

    except Exception as e:
        return {
            "rows": [],
            "columns": [],
            "count": 0,
            "message": f"Error executing query: {str(e)}",
        }


sql_tool = StructuredTool.from_function(
    name="sql_tool",
    coroutine=execute_sql_query,
    args_schema=SQLQueryInput,
    description="Executes a SQL query and returns rows with labeled column names.",
    return_direct=True,
)
