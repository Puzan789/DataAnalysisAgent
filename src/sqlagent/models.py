from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class ChunkType(str, Enum):
    TABLE = "table"
    COLUMN = "column"
    RELATIONSHIP = "relationship"
    FOREIGNKEY = "foreignkey"
    EXAMPLE_QUERY = "example_query"


class ChunkMetadata(BaseModel):
    """Metadata for each semantic chunk stored in Qdrant."""

    # Required fields
    type: ChunkType = Field(..., description="Type of chunk")
    table_name: str = Field(..., description="Table name")
    description: str = Field(
        ..., description="Natural language description of the chunk"
    )

    # Optional fields based on chunk type
    schema_name: str = Field(default="public", description="Database schema name")
    column_name: Optional[str] = Field(
        None, description="Column name (for column chunks)"
    )
    fk_from: Optional[str] = Field(
        None, description="Foreign key source (for relationship chunks)"
    )
    fk_to: Optional[str] = Field(
        None, description="Foreign key target (for relationship chunks)"
    )

    # Domain and categorization
    domain_tags: list[str] = Field(
        default_factory=list, description="Domain tags for filtering"
    )
    example_questions: list[str] = Field(
        default_factory=list, description="Example questions this chunk helps answer"
    )
    # Additional context
    data_type: Optional[str] = Field(None, description="Data type (for columns)")
    example_values: list[str] = Field(
        default_factory=list, description="Example values (for columns)"
    )
    cardinality: Optional[str] = Field(
        None, description="Cardinality (for relationships)"
    )

    class Config:
        use_enum_values = True

    def filter_dict(self):
        """Filter the dictionary representation of the object to exclude empty or default values."""
        # Convert the Pydantic model to a dictionary
        fields_dict = self.model_dump(
            exclude_unset=True, exclude_none=True, exclude_defaults=True
        )

        return fields_dict


class RetrievalResult(BaseModel):
    """Result from vector search."""

    chunk_id: str
    chunk_type: ChunkType
    content: str
    metadata: ChunkMetadata
    score: float = Field(..., description="Similarity score")


class ColumnChunk(BaseModel):
    """Semantic chunk for a database column."""

    table_name: str
    column_name: str
    schema_name: str = "public"
    meaning: str = Field(..., description="What this column represents")
    data_type: str = Field(..., description="Data type")
    example_values: list[str] = Field(default_factory=list, description="Sample values")
    units: Optional[str] = Field(None, description="Units of measurement if applicable")
    related_columns: list[str] = Field(
        default_factory=list, description="Related columns"
    )
    synonyms: list[str] = Field(default_factory=list, description="Alternative terms")

    def to_text(self) -> str:
        """Convert to natural language text for embedding."""
        text_parts = [
            f"Column: {self.schema_name}.{self.table_name}.{self.column_name}",
            f"Meaning: {self.meaning}",
            f"Data Type: {self.data_type}",
        ]

        if self.example_values:
            values_str = ", ".join(f'"{v}"' for v in self.example_values[:3])
            text_parts.append(f"Example values: {values_str}")

        if self.units:
            text_parts.append(f"Units: {self.units}")

        if self.related_columns:
            rel_str = ", ".join(self.related_columns)
            text_parts.append(f"Related columns: {rel_str}")

        if self.synonyms:
            syn_str = ", ".join(self.synonyms)
            text_parts.append(f"Also known as: {syn_str}")

        return "\n".join(text_parts)


class RelationshipChunk(BaseModel):
    """Semantic chunk for a database relationship."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    schema_name: str = "public"
    description: str = Field(..., description="What this relationship represents")
    join_purpose: str = Field(..., description="Why you'd join these tables")

    def to_text(self) -> str:
        """Convert to natural language text for embedding."""
        fk_from = f"{self.schema_name}.{self.from_table}.{self.from_column}"
        fk_to = f"{self.schema_name}.{self.to_table}.{self.to_column}"

        return f"""Relationship:
{fk_from} → {fk_to}
Description: {self.description}
Usage: {self.join_purpose}"""


class TableChunk(BaseModel):
    """Semantic chunk for a database table."""

    table_name: str
    description: str = Field(..., description="High-level purpose of the table")
    columns: list[str] = Field(..., description="List of column names in the table")

    def to_text(self) -> str:
        """Convert to natural language text for embedding."""
        text_parts = [
            f"table_name: {self.table_name}",
            f"description: {self.description}",
            f"columns: {self.columns}",
        ]
        return "\n".join(text_parts)
