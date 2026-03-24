from fastapi import APIRouter
from src.core.utils import get_embeddings
from src.core.responses import APIResponse
from loguru import logger
from src.core.exception import CustomException
from src.sqlagent.indexer import schema_indexer
from src.sqlagent.embeddings.vectorstore import VectorStore
from src.config import settings

vector_router = APIRouter(prefix="/vector", tags=["Vector Database"])
vector_embedding = get_embeddings()


@vector_router.post("/initialize_schema")
async def initialize_vector_schema():
    """Initialize the vector database with database schema information used for retreival of while generating SQL"""
    try:
        indexer = schema_indexer.SchemaIndexer()
        indexer.init_schema()
        return APIResponse(
            success=True,
            message="Database schema indexed successfully",
        )
    except Exception as e:
        logger.error(f"Error initializing database schema in vector store: {e}")
        raise CustomException(
            message="Failed to initialize database schema in vector store."
        )


@vector_router.get("/stats")
async def get_vector_stats():
    """Return basic stats about the vector collections used by the SQL agent."""
    try:
        table_store = VectorStore(settings.TABLE_DESCRIPTION_COLLECTION)
        schema_store = VectorStore(settings.DB_SCHEMA_COLLECTION)

        collections = []
        for store, payload_types in [
            (table_store, ["TABLE_DESCRIPTION"]),
            (schema_store, ["TABLE_SCHEMA"]),
        ]:
            info = store.get_collection_info()
            counts = store.count_by_payload_types(payload_types)
            if "TABLE_SCHEMA" in payload_types:
                chunk_type_counts = store.count_schema_entity_types()
            else:
                chunk_type_counts = {
                    "table": counts.get("TABLE_DESCRIPTION", 0),
                    "column": 0,
                    "relationship": 0,
                    "foreignkey": 0,
                    "example_query": 0,
                }
            collections.append(
                {**info, "counts": counts, "chunk_type_counts": chunk_type_counts}
            )

        total_vectors = sum(item.get("vectors_count", 0) or 0 for item in collections)
        total_points = sum(item.get("points_count", 0) or 0 for item in collections)

        return APIResponse(
            success=True,
            message="Vector store stats",
            data={
                "qdrant_url": settings.QDRANT_URL,
                "collections": collections,
                "total_vectors": total_vectors,
                "total_points": total_points,
            },
        )
    except Exception as e:
        logger.error(f"Error fetching vector store stats: {e}")
        raise CustomException(message="Failed to fetch vector store stats.")
