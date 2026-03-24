import json
import uuid
from typing import Dict, List, Optional, Any
from loguru import logger
from langchain_core.documents import Document
from src.config import settings
from src.sqlagent.models import (
    ChunkType,
    ChunkMetadata,
    TableChunk,
    ColumnChunk,
    RelationshipChunk,
)


class ChunkGenerator:
    """Generate semantic and technical chunks from schema information"""

    def __init__(self):
        self.embedding_model = settings.EMBEDDING_MODEL
        self.column_batch_size = 50

    def _infer_table_purpose(self, table_name: str):
        clean_name = table_name.replace("tbl_", "").replace("_table", "")
        return f"Stores information about {clean_name.replace('_', ' ')}"

    def _infer_column_meaning(self, column_name: str, data_type: str) -> str:
        if column_name.endswith("_id"):
            entity = column_name.replace("_id", "")
            return f"Unique identifier for {entity.replace('_', ' ')}"
        if column_name.endswith("_date") or column_name.endswith("_at"):
            event = column_name.replace("_date", "").replace("_at", "")
            return f"Date/time when {event.replace('_', ' ')} occurred"
        if column_name.startswith("is_") or column_name.startswith("has_"):
            condition = column_name.replace("is_", "").replace("has_", "")
            return f"Boolean flag indicating {condition.replace('_', ' ')}"
        return f"Represents the {column_name.replace('_', ' ')} value"

    def generate_table_chunk(self, table_info, key_columns: list[str] | None = None):
        schema_name = table_info["schema"]
        table_name = table_info["table_name"]
        columns = table_info["columns"]

        if key_columns is None:
            key_columns_output = [f"{col} " for col in columns]
        else:
            key_columns_output = [
                f"{col_name}" for col_name in key_columns if col_name in columns
            ]

        purpose = table_info.get("table_comment", "") or self._infer_table_purpose(
            table_name
        )

        return TableChunk(
            table_name=table_name,
            schema_name=schema_name,
            description=purpose,
            columns=key_columns_output,
        )

    def generate_column_chunk(self, column_info, table_info, schema_extractor):
        schema_name = column_info["schema"]
        table_name = column_info["table_name"]
        column_name = column_info["column_name"]
        data_type = column_info["type"]

        sample_values = schema_extractor._get_sample_value(
            table_name, column_name, schema_name
        )[:5]
        sample_values = [str(v) for v in sample_values]
        meaning = column_info.get("comment", "") or self._infer_column_meaning(
            column_name, data_type
        )

        return ColumnChunk(
            table_name=table_name,
            column_name=column_name,
            schema_name=schema_name,
            meaning=meaning,
            data_type=data_type,
            example_values=sample_values,
        )

    def generate_relationship_chunk(self, relationship_info):
        from_table = relationship_info["from_table"]
        from_columns = relationship_info["from_columns"]
        to_table = relationship_info["to_table"]
        to_columns = relationship_info["to_columns"]
        schema_name = relationship_info["from_schema"]

        from_column = from_columns[0] if from_columns else "id"
        to_column = to_columns[0] if to_columns else "id"

        description = (
            f"Each {from_table} record references a {to_table} record via {from_column}"
        )
        join_purpose = f"Join {from_table} to {to_table} to get additional details about the referenced {to_table.rstrip('s')}"

        return RelationshipChunk(
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column,
            schema_name=schema_name,
            description=description,
            join_purpose=join_purpose,
        )

    def generate_db_schema_chunks(
        self,
        schema_extractor,
        schema: str = "public",
        project_id: Optional[str] = None,
    ) -> List[Document]:
        documents = []
        tables_info = schema_extractor.extract_all_tables(schema=schema)

        for table_info in tables_info:
            table_doc = self._create_table_document(table_info, project_id)
            documents.append(table_doc)

            column_docs = self._create_column_documents(
                schema_extractor, table_info, schema, project_id
            )
            documents.extend(column_docs)

        return documents

    def _create_table_document(
        self, table_info: Dict, project_id: Optional[str] = None
    ) -> Document:
        table_name = table_info["table_name"]
        description = table_info.get("table_comment", f"{table_name} table")

        # FIX: Use simple dict structure, avoid nested json.dumps()
        payload = {
            "type": "TABLE",
            "name": table_name,
            "alias": table_name,
            "description": description,
        }

        metadata = {
            "type": "TABLE_SCHEMA",
            "name": table_name,
            "doc_id": str(uuid.uuid4()),
        }
        if project_id:
            metadata["project_id"] = project_id

        return Document(page_content=json.dumps(payload), metadata=metadata)

    def _create_column_documents(
        self,
        schema_extractor,
        table_info: Dict,
        schema: str,
        project_id: Optional[str] = None,
    ) -> List[Document]:
        table_name = table_info["table_name"]
        columns = []

        for col_name in table_info["columns"]:
            try:
                col_details = schema_extractor.extract_column_details(
                    table_name, col_name, schema=schema
                )
                columns.append(
                    {
                        "type": "COLUMN",
                        "comment": col_details.get("comment", ""),
                        "name": col_details["column_name"],
                        "data_type": col_details["data_type"].upper(),
                        "is_primary_key": col_details["is_primary_key"],
                    }
                )
            except Exception as e:
                logger.error(
                    f"Error extracting column {col_name} for {table_name}: {e}"
                )

        try:
            relationships = schema_extractor.extract_relationship(
                table_name, schema=schema
            )
            for rel in relationships:
                columns.append(
                    {
                        "type": "FOREIGN_KEY",
                        "comment": rel["comment"],
                        "constraint": rel["constraint"],
                        "tables": rel["tables"],
                    }
                )
        except Exception as e:
            print(f"Error extracting relationships for {table_name}: {e}")

        documents = []
        for i in range(0, len(columns), self.column_batch_size):
            batch = columns[i : i + self.column_batch_size]
            payload = {"type": "TABLE_COLUMNS", "columns": batch}

            metadata = {
                "type": "TABLE_SCHEMA",
                "name": table_name,
                "doc_id": str(uuid.uuid4()),
            }
            if project_id:
                metadata["project_id"] = project_id

            doc = Document(page_content=json.dumps(payload), metadata=metadata)
            documents.append(doc)

        return documents

    def chunk_to_metadata(self, chunk: Any, chunk_type: ChunkType):
        """Convert a chunk to metadata for storage."""
        metadata = ChunkMetadata(
            type=chunk_type,
            table_name=chunk.table_name,
            schema_name=getattr(chunk, "schema_name", "public"),
            description=chunk.to_text(),
        )

        if chunk_type == ChunkType.COLUMN:
            metadata.column_name = chunk.column_name
            metadata.data_type = chunk.data_type
            metadata.example_values = chunk.example_values

        elif chunk_type == ChunkType.RELATIONSHIP:
            metadata.fk_from = f"{chunk.from_table}.{chunk.from_column}"
            metadata.fk_to = f"{chunk.to_table}.{chunk.to_column}"

        return metadata.filter_dict()
