
import json
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from src.prompts.chart_prompts import (
    CHART_GENERATION_SYSTEM_PROMPT,
    get_chart_generation_prompt,
    CHART_ADJUSTMENT_SYSTEM_PROMPT,
    get_chart_adjustment_prompt,
)
from src.sqlagent.nodes.sql_execution import execute_sql_with_async


VALID_CHART_TYPES = {"line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area"}


def parse_chart_response(raw_content: str) -> dict:
    """Parse LLM response as JSON, handling markdown code fences."""
    text = raw_content.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


class ChartAdjustmentOption(BaseModel):
    chart_type: str | None = None
    x_axis: str | None = None
    y_axis: str | None = None
    x_offset: str | None = None
    color: str | None = None


def preprocess_data(data: dict, max_rows: int = 15, max_unique: int = 5) -> dict:
    """Sample rows and extract unique column values for the LLM prompt."""
    columns = data.get("columns", [])
    rows = data.get("results", [])

    sample_data = rows[:max_rows]

    sample_column_values = {}
    for col in columns:
        unique_vals = list({str(row.get(col, "")) for row in rows if row.get(col) is not None})
        sample_column_values[col] = unique_vals[:max_unique]

    return {
        "sample_data": sample_data,
        "columns": columns,
        "sample_column_values": sample_column_values,
    }




def validate_vega_lite_schema(chart_schema: dict) -> bool:
    """Basic validation of the Vega-Lite schema structure."""
    if not chart_schema:
        return False
    if not isinstance(chart_schema, dict):
        return False
    # Must have mark and encoding at minimum
    if "mark" not in chart_schema:
        return False
    if "encoding" not in chart_schema:
        return False
    return True


def inject_data_into_schema(chart_schema: dict, data: list[dict]) -> dict:
    """Inject actual data values into the Vega-Lite schema."""
    if not chart_schema:
        return chart_schema
    schema = chart_schema.copy()
    # Serialize values safely (handle dates, decimals, etc.)
    safe_data = json.loads(json.dumps(data, default=str))
    schema["data"] = {"values": safe_data}
    return schema


class ChartResult(BaseModel):
    status: Literal["generating", "fetching", "finished", "failed", "stopped"] = "generating"
    error: str | None = None
    reasoning: str = ""
    chart_type: str = ""
    chart_schema: dict = Field(default_factory=dict)


class ChartService:
    def __init__(self, llm):
        self.llm = llm
        self._results: dict[str, ChartResult] = {}

    def get_result(self, query_id: str) -> ChartResult | None:
        return self._results.get(query_id)

    def stop(self, query_id: str) -> bool:
        if query_id in self._results:
            self._results[query_id] = ChartResult(status="stopped")
            return True
        return False

    async def _call_llm_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call LLM with json_mode and parse the response."""
        llm_with_json = self.llm.bind(
            response_format={"type": "json_object"}
        )
        response = await llm_with_json.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return parse_chart_response(response.content)

    async def generate_chart(
        self,
        query_id: str,
        query: str,
        sql: str,
        data: dict | None = None,
    ):
        """Background task: fetch data if needed, then generate chart via LLM."""
        try:
            # Step 1: Fetch data if not provided
            if data is None:
                self._results[query_id] = ChartResult(status="fetching")
                data = await execute_sql_with_async(sql)
                if not data.get("success"):
                    self._results[query_id] = ChartResult(
                        status="failed",
                        error=data.get("error", "SQL execution failed"),
                    )
                    return

            # Check if stopped
            if self._results.get(query_id, ChartResult()).status == "stopped":
                return

            self._results[query_id] = ChartResult(status="generating")

            # Step 2: Preprocess data
            preprocessed = preprocess_data(data)
            rows = data.get("results", [])

            if len(rows) < 2 or len(preprocessed["columns"]) < 1:
                self._results[query_id] = ChartResult(
                    status="failed",
                    error="Insufficient data for chart generation (need at least 2 rows).",
                )
                return

            # Step 3: Build prompt and call LLM with json_mode
            user_prompt = get_chart_generation_prompt(
                query=query,
                sql=sql,
                sample_data=preprocessed["sample_data"],
                columns=preprocessed["columns"],
                sample_column_values=preprocessed["sample_column_values"],
            )

            parsed = await self._call_llm_json(CHART_GENERATION_SYSTEM_PROMPT, user_prompt)

            reasoning = parsed.get("reasoning", "")
            chart_type = parsed.get("chart_type", "")
            chart_schema = parsed.get("chart_schema", {})

            # Check if stopped
            if self._results.get(query_id, ChartResult()).status == "stopped":
                return

            # Step 4: Validate and inject data
            if chart_type not in VALID_CHART_TYPES or not validate_vega_lite_schema(chart_schema):
                self._results[query_id] = ChartResult(
                    status="failed",
                    error="No suitable chart could be generated for this data.",
                    reasoning=reasoning,
                )
                return

            chart_schema.setdefault(
                "$schema", "https://vega.github.io/schema/vega-lite/v5.json"
            )

            # Inject full data into schema
            chart_with_data = inject_data_into_schema(chart_schema, rows)

            self._results[query_id] = ChartResult(
                status="finished",
                reasoning=reasoning,
                chart_type=chart_type,
                chart_schema=chart_with_data,
            )
            logger.info(f"[ChartService] Chart generated: {query_id} type={chart_type}")

        except Exception as e:
            logger.error(f"[ChartService] Error generating chart {query_id}: {e}")
            self._results[query_id] = ChartResult(
                status="failed",
                error=str(e),
            )

    async def adjust_chart(
        self,
        query_id: str,
        query: str,
        sql: str,
        chart_schema: dict,
        adjustment_option: dict,
        data: dict | None = None,
    ):
        """Background task: adjust an existing chart."""
        try:
            if data is None:
                self._results[query_id] = ChartResult(status="fetching")
                data = await execute_sql_with_async(sql)
                if not data.get("success"):
                    self._results[query_id] = ChartResult(
                        status="failed",
                        error=data.get("error", "SQL execution failed"),
                    )
                    return

            self._results[query_id] = ChartResult(status="generating")

            user_prompt = get_chart_adjustment_prompt(
                query=query,
                sql=sql,
                chart_schema=chart_schema,
                adjustment_option=adjustment_option,
            )

            parsed = await self._call_llm_json(CHART_ADJUSTMENT_SYSTEM_PROMPT, user_prompt)

            reasoning = parsed.get("reasoning", "")
            chart_type = parsed.get("chart_type", "")
            result_schema = parsed.get("chart_schema", {})

            if chart_type not in VALID_CHART_TYPES or not validate_vega_lite_schema(result_schema):
                self._results[query_id] = ChartResult(
                    status="failed",
                    error="Chart adjustment failed.",
                    reasoning=reasoning,
                )
                return

            result_schema.setdefault(
                "$schema", "https://vega.github.io/schema/vega-lite/v5.json"
            )
            rows = data.get("results", [])
            chart_with_data = inject_data_into_schema(result_schema, rows)

            self._results[query_id] = ChartResult(
                status="finished",
                reasoning=reasoning,
                chart_type=chart_type,
                chart_schema=chart_with_data,
            )

        except Exception as e:
            logger.error(f"[ChartService] Error adjusting chart {query_id}: {e}")
            self._results[query_id] = ChartResult(
                status="failed",
                error=str(e),
            )
