from pydantic import BaseModel, Field

class CompanyInfoInput(BaseModel):
    query: str = Field(description="The search query to retrieve relevant information from the system documentation")


class SQLQueryInput(BaseModel):
    query: str