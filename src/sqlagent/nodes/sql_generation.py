from langgraph.prebuilt import create_react_agent
from jinja2 import Template
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import datetime
from langchain_openai import ChatOpenAI
from lark import logger
from src.tools.sql_execution_tool import sql_tool
from src.config import settings

llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_KEY)
TEXT_TO_SQL_RULES = """
### SQL RULES ###
- Use ANSI SQL (PostgreSQL dialect)
- ONLY SELECT statements (no DELETE/UPDATE/INSERT)
- Use tables/columns from schema only
- **CRITICAL: If table or column names use uppercase or mixed case (e.g. "Track", "AlbumId"), you MUST wrap them in double quotes in the SQL query.** Example: SELECT "Name" FROM "Track"
- Use JOIN when selecting from multiple tables
- Use lower() for case-insensitive comparisons: `lower("column") LIKE lower('%value%')`
- Use wildcards (%) for flexible matching
- Prefer CTEs over subqueries
- No comments in SQL
- Use HAVING (not WHERE) for aggregate filtering
- Use subqueries for window function filtering (DENSE_RANK, ROW_NUMBER)
- Limit results with LIMIT 8 (or as appropriate)
"""

sql_generation_system_prompt = f"""
You are a SQL generation assistant that MUST use the sql_tool to execute queries against the database.

### YOUR TASK ###
1. Understand user intent - recognize abbreviations, alternative names, and semantic variations
2. Generate a SELECT query based on the provided database schema
3. **IMMEDIATELY call the sql_tool** with your generated SQL query

### UNDERSTANDING USER QUERIES ###
- Recognize common abbreviations and alternative names
- Use flexible matching with OR conditions and wildcards for broader results
- Use `lower()` for case-insensitive comparisons

{TEXT_TO_SQL_RULES}

### CRITICAL - ALWAYS USE THE sql_tool ###
After generating SQL, you MUST call: sql_tool(query="YOUR_SQL_HERE")
DO NOT return SQL as text - you MUST invoke the tool!

"""
sql_generation_user_prompt_template = """
### DATABASE SCHEMA ###
{% for document in documents %}
    {{ document }}
{% endfor %}

{% if calculated_field_instructions %}
{{ calculated_field_instructions }}
{% endif %}

{% if metric_instructions %}
{{ metric_instructions }}
{% endif %}

{% if json_field_instructions %}
{{ json_field_instructions }}
{% endif %}

{% if sql_functions %}
### SQL FUNCTIONS ###
{% for function in sql_functions %}
{{ function }}
{% endfor %}
{% endif %}

{% if sql_samples %}
### SQL SAMPLES ###
{% for sample in sql_samples %}
Question:
{{sample.question}}
SQL:
{{sample.sql}}
{% endfor %}
{% endif %}

{% if instructions %}
### USER INSTRUCTIONS ###
{% for instruction in instructions %}
{{ loop.index }}. {{ instruction }}
{% endfor %}
{% endif %}

### CRITICAL REQUIREMENTS ###
- Use the database schema provided above to determine the correct tables and columns
- Always include the primary table's `id` column in SELECT
- Use semantic/flexible matching with OR and wildcards (%) to catch variations
- Use `lower()` for case-insensitive comparisons
- LIMIT results appropriately (default LIMIT 8)

### QUESTION ###
User's Question: {{ query }}

{% if sql_generation_reasoning %}
### REASONING PLAN ###
{{ sql_generation_reasoning }}
{% endif %}

Let's think step by step.
"""


async def sql_generation_node(state: dict):
    tools = [sql_tool]
    template = Template(sql_generation_user_prompt_template)

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

    rendered_prompt = template.render(
        documents=documents,
        sql_samples=state.get("sql_samples", []),
        sql_functions=state.get("sql_functions", []),
        instructions=state.get("instructions", []),
        # Use reasoning from previous node
        query=state.get("query", ""),
        language=state.get("language", "English"),
        current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    messages = [
        SystemMessage(content=sql_generation_system_prompt),
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
