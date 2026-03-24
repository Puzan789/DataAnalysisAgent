from src.sqlagent.embeddings.embedder import OpenAIEmbedder
from src.sqlagent.embeddings.vectorstore import VectorStore
from src.config import settings
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
import json
from loguru import logger


class Retriever:
    def __init__(self):
        self.embedder = OpenAIEmbedder()
        self.table_descriptions_store = VectorStore(
            settings.TABLE_DESCRIPTION_COLLECTION
        )
        self.db_schema_store = VectorStore(settings.DB_SCHEMA_COLLECTION)

    def retrieve_table_descriptions(
        self, query: str, top_k: int = 10, min_score: float = 0.0
    ):
        """semantic search on table_descriptions"""
        logger.info(f"- Semantic search for query: {query}")
        query_embedding = self.embedder.embed_texts([query])[0]
        logger.info(f"- Query embedding generated of length {len(query_embedding)}")
        results = self.table_descriptions_store.client.search(
            collection_name=settings.TABLE_DESCRIPTION_COLLECTION,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="type", match=MatchValue(value="TABLE_DESCRIPTION")
                    )
                ]
            ),
            with_payload=True,
            score_threshold=min_score,
        )
        logger.info(f"- Retrieved {len(results)} relevant table descriptions")
        # Extract table names and metadata
        relevant_tables = []
        for result in results:
            relevant_tables.append(
                {
                    "table_name": result.payload["table_name"],
                    "description": result.payload["description"],
                    "score": result.score,
                    "payload": result.payload,
                }
            )
        return relevant_tables

    def retrieve_db_schemas_by_filter(self, table_names, limit: int = 100):
        """Stage 2: Technical lookup on db_schemas using FILTER ONLY (no vector search).
        Retrieves ALL schema documents for the given table names."""
        if not table_names:
            logger.warning("No table names provided for schema retrieval.")
            return []
        logger.info(f"- Retrieving DB schemas for tables: {table_names}")
        # NOTE: Using scroll (no vector needed) with filter
        # CRITICAL FIX: Filter by BOTH type AND table_names to avoid retrieving all tables
        scroll_result = self.db_schema_store.client.scroll(
            collection_name=settings.DB_SCHEMA_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="type", match=MatchValue(value="TABLE_SCHEMA")),
                    FieldCondition(key="table_name", match=MatchAny(any=table_names)),
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        schema_documents = []
        for point in scroll_result[0]:
            schema_documents.append(
                {
                    "table_name": point.payload["table_name"],
                    "description": point.payload["description"],
                    "type": point.payload["type"],
                    "payload": point.payload,
                }
            )
        logger.info(
            f"Retrieved {len(schema_documents)} schema documents for provided table names."
        )
        return schema_documents

    def reassemble_schemas(self, schema_documents: list):
        """
        Stage 3: Reassemble complete table schemas from retrieved documents.
        Groups columns, foreign keys, and table metadata by table name.
        """
        logger.info(
            f"Stage 3 - Reassembling schemas from {len(schema_documents)} documents"
        )

        schemas = {}
        for doc in schema_documents:
            table_name = doc["table_name"]
            schema_content = json.loads(doc["description"])

            if table_name not in schemas:
                schemas[table_name] = {
                    "table_name": table_name,
                    "columns": [],
                    "foreign_keys": [],
                    "table_metadata": None,
                }

            # Handle different document types
            if schema_content.get("type") == "TABLE":
                schemas[table_name]["table_metadata"] = schema_content

            elif schema_content.get("type") == "TABLE_COLUMNS":
                # Process column batch
                for col in schema_content.get("columns", []):
                    if col["type"] == "COLUMN":
                        schemas[table_name]["columns"].append(col)
                    elif col["type"] == "FOREIGN_KEY":
                        schemas[table_name]["foreign_keys"].append(col)

        logger.info(
            f"Stage 3 complete - Reassembled {len(schemas)} complete table schemas"
        )
        return schemas

    def construct_db_schemas(self, schemas):
        """Construct clean DDL-like text representation for LLM prompting"""
        logger.info("- Constructing DB schema text representation for prompting")
        ddl_statements = []
        for table_name, schema in schemas.items():
            ddl_parts = []

            # Add table comment/description (cleaner format)
            if schema["table_metadata"]:
                table_meta = schema["table_metadata"]
                desc = table_meta.get("description", table_meta.get("comment", ""))
                if desc:
                    ddl_parts.append(f"-- {table_name}: {desc}")

            ddl_parts.append(f"CREATE TABLE {table_name} (")

            # columns
            column_defs = []
            for col in schema["columns"]:
                col_def = f"{col['name']} {col['data_type']}"
                if col.get("is_primary_key"):
                    col_def += " PRIMARY KEY"
                if col.get("comment"):
                    col_def += f" -- {col['comment']}"
                column_defs.append(f"  {col_def}")
            ddl_parts.append(",\n".join(column_defs))

            # Foreign keys (cleaner format)
            if schema["foreign_keys"]:
                for fk in schema["foreign_keys"]:
                    fk_line = f",\n  {fk['constraint']}"
                    # Clean up foreign key comments - extract just the condition
                    if fk.get("comment"):
                        try:
                            comment_data = json.loads(fk["comment"].replace("-- ", ""))
                            condition = comment_data.get("condition", "")
                            if condition:
                                fk_line += f"  -- {condition}"
                        except (json.JSONDecodeError, KeyError, AttributeError):
                            # If parsing fails, skip the messy comment
                            pass
                    ddl_parts.append(fk_line)

            ddl_parts.append("\n);")

            ddl_statements.append("\n".join(ddl_parts))
        logger.info(f"Constructed DDL for {len(ddl_statements)} DDL statements")
        return ddl_statements

    def construct_retrieval_results(self, ddl_statements):
        """Construct retrieval results for LLM context."""
        retrieval_results = []
        for ddl in ddl_statements:
            # Extract table name from DDL (simple parse)
            table_name = ddl.split("CREATE TABLE ")[1].split(" (")[0].strip()
            retrieval_results.append(
                {
                    "table_name": table_name,
                    "table_ddl": ddl,
                }
            )

        return {
            "retrieval_results": retrieval_results,
        }

    def retriever(self, query, top_k_tables: int = 5, schema_limit: int = 100):
        """Complete retrieval pipeline to get relevant table description and db_Schemas"""
        logger.info(f"Starting retrieval pipeline for query: {query}")
        # Step 1: Retrieve relevant table descriptions
        table_results = self.retrieve_table_descriptions(
            query=query, top_k=top_k_tables
        )
        table_names = [t["table_name"] for t in table_results]
        logger.info(f"Relevant table names: {table_names}")

        # Step 2: Retrieve DB schemas by filter
        schema_documents = self.retrieve_db_schemas_by_filter(
            table_names, limit=schema_limit
        )
        # Step 3: Reassemble complete schemas
        reassembled_schemas = self.reassemble_schemas(schema_documents)
        # Step 4: Construct DDL-like text representation
        ddl_statements = self.construct_db_schemas(reassembled_schemas)
        # Step 5: Construct retrieval results for LLM context
        retrieval_output = self.construct_retrieval_results(ddl_statements)

        retrieval_results = {
            "query": query,
            "retrieval_results": retrieval_output["retrieval_results"],
        }
        logger.info(f"Retrieval pipeline complete for query: {query}")
        return retrieval_results

    def to_documents(self, retrieval_results):
        """Convert retrieval results to LangGraph Document objects."""
        from langchain_core.documents import Document

        documents = []
        for item in retrieval_results["retrieval_results"]:
            doc = Document(
                page_content=item["table_ddl"],
                metadata={
                    "table_name": item["table_name"],
                },
            )
            documents.append(doc)

        return documents

    def format_context_for_llm(self, retrieval_results):
        """The function converts the retrieval bundle into a Markdown summary with relevant tables and fenced SQL DDL blocks."""
        context_parts = []

        # Add relevant tables with scores
        if retrieval_results.get("relevant_tables"):
            context_parts.append("## Relevant Tables (Semantic Search):\n")
            for table in retrieval_results["relevant_tables"]:
                context_parts.append(
                    f"- **{table['table_name']}** (relevance: {table['score']:.2f})"
                )
                context_parts.append(f"  {table['description']}\n")

        # Add complete DDL schemas
        if retrieval_results.get("ddl_statements"):
            context_parts.append("\n## Complete Database Schemas:\n")
            for ddl in retrieval_results["ddl_statements"]:
                context_parts.append(f"```sql\n{ddl}\n```\n")

        return "\n".join(context_parts)
