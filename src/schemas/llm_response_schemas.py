from pydantic import BaseModel, Field
from typing import Literal


class EvaluationResponse(BaseModel):
    approval: bool = Field(
        description="Whether the tool results are enough to answer user query or not."
    )
    reasoning: str | None = Field(
        default=None,
        description="Suggestions for improving the SQL query or reasoning for disapproval.",
    )


class RouterResponse(BaseModel):
    route_to: Literal["sql_agents", "general_agent"] = Field(
        description="Which agent should respond to the user_query"
    )
