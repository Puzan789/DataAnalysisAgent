from qdrant_client import QdrantClient, models
from qdrant_client.models import FieldCondition, MatchAny, MatchValue, Filter
from src.config import settings
from loguru import logger
from uuid import uuid4
from src.sqlagent.models import ChunkMetadata, ChunkType, RetrievalResult
import json


class VectorStore:
    """Wrapper around Qdrant vector store for managing embeddings and metadata."""

    def __init__(self, collection_name: str = None):
        self.client = QdrantClient(
            url=settings.QDRANT_URL
        )  # NOTE: consider adding api key if needed
        self.collection_name = collection_name

    def create_collection(self, vector_size: int = 1536):
        """Create a Qdrant collection with specified vector size."""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
        self._create_payload_indexes()

    def _create_payload_indexes(self):
        """Create indexes on frequently queried metadata fields."""
        index_fields = ["type", "table_name"]
        for field in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema="keyword",
                )
                logger.info(
                    f"Created index on '{field}' for collection '{self.collection_name}'"
                )
            except Exception as e:
                logger.info(f" Index on '{field}' may already exist or error: {e}")

    def upsert_chunks(
        self, embeddings, metadata_list, chunk_ids: str | None = None
    ):  # metadata_list is the list of the chunks we send earlier
        """Upsert chunks into the Qdrant collection"""
        if chunk_ids is None:
            chunk_ids = [str(uuid4()) for _ in range(len(embeddings))]
        points = []
        for chunk_id, embedding, metadata in zip(chunk_ids, embeddings, metadata_list):
            point = models.PointStruct(id=chunk_id, vector=embedding, payload=metadata)
            points.append(point)
        self.client.upsert(collection_name=self.collection_name, points=points)

    # NOTE:Instead of client.search we can use this another query_points in qdrant sending batch of vectors to search
    def search(
        self,
        query_vector,
        top_k,
        chunk_type,
        table_names=None,
        schema_name=None,
        domain_tags=None,
        min_score: int | None = None,
    ):
        """Search for the similar chunk with the filtering the case"""
        # build filter conditions
        must_conditions = []
        if chunk_type:
            must_conditions.append(
                models.FieldCondition(
                    key="type", match=models.MatchValue(value=chunk_type.value)
                )
            )
        if table_names:
            must_conditions.append(
                FieldCondition(key="table_name", match=MatchAny(any=table_names))
            )

        if schema_name:
            must_conditions.append(
                FieldCondition(key="schema_name", match=MatchValue(value=schema_name))
            )

        if domain_tags:
            must_conditions.append(
                FieldCondition(key="domain_tags", match=MatchAny(any=domain_tags))
            )
        search_filter = Filter(must=must_conditions) if must_conditions else None

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
            score_threshold=min_score,  # filter out the score lower than this it is Optional can remove it
        )
        retrieval_results = []
        for result in results:
            metadata = ChunkMetadata(**result.payload)
            retrieval_result = RetrievalResult(
                chunk_id=str(result.id),
                chunk_type=ChunkType(metadata.type),
                content=metadata.description,
                metadata=metadata,
                score=result.score,
            )
            retrieval_results.append(retrieval_result)
        print((f"Found {len(retrieval_results)} results (top_k={top_k})"))
        return retrieval_results

    def get_chunk(self, chunk_id: str):
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id],
                with_payload=True,
                with_vectors=False,
            )
            if result:
                point = result[0]
                metadata = ChunkMetadata(**point.payload)
                return RetrievalResult(
                    chunk_id=str(point.id),
                    chunk_type=ChunkType(metadata.type),
                    content=metadata.description,
                    score=1.0,
                )
        except Exception as e:
            print(f"There is error in getting a specifinc chunk {e}")
            return None

    def delete_chunks(
        self,
        chunk_ids: str | None = None,
        table_name: str | None = None,
        chunk_type: ChunkType | None = None,
    ):
        """Delete chunks by Id or filter"""
        if chunk_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids,
            )
            print("Deleted chunks")  # use logger here
        elif table_name or chunk_type:
            conditions = []
            if table_name:
                conditions.append(
                    FieldCondition(key="table_name", match=MatchValue(value=table_name))
                )
            if chunk_type:
                conditions.append(
                    FieldCondition(key="type", match=MatchValue(value=chunk_type.value))
                )
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=conditions),
            )
            print("DEleted")

    def get_collection_info(self):
        """Get basic and configuration info about the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            config = getattr(info, "config", None)
            params = getattr(config, "params", None) if config else None
            vectors = getattr(params, "vectors", None) if params else None

            vector_size = None
            distance_metric = None
            if vectors:
                if hasattr(vectors, "size"):
                    vector_size = vectors.size
                elif isinstance(vectors, dict):
                    vector_size = vectors.get("size")

                if hasattr(vectors, "distance"):
                    distance_metric = getattr(vectors, "distance", None)
                elif isinstance(vectors, dict):
                    distance_metric = vectors.get("distance")

            # HNSW params if available
            hnsw_config = getattr(config, "hnsw_config", None) if config else None
            hnsw_ef_construct = getattr(hnsw_config, "ef_construct", None)
            hnsw_m = getattr(hnsw_config, "m", None)

            # Optimizer/shard info if available
            optimizer_status = getattr(info, "optimizer_status", None)
            shard_number = getattr(info, "shard_number", None)
            replication_factor = getattr(info, "replication_factor", None)

            return {
                "name": self.collection_name,
                "vectors_count": getattr(info, "vectors_count", 0) or 0,
                "points_count": getattr(info, "points_count", 0) or 0,
                "status": getattr(info, "status", "unknown"),
                "vector_size": vector_size,
                "distance_metric": distance_metric,
                "segments_count": getattr(info, "segments_count", None),
                "hnsw_ef_construct": hnsw_ef_construct,
                "hnsw_m": hnsw_m,
                "shard_number": shard_number,
                "replication_factor": replication_factor,
                "optimizer_status": optimizer_status,
            }
        except Exception as e:
            logger.error(
                f"Error getting collection info for {self.collection_name}: {e}"
            )
            return {
                "name": self.collection_name,
                "vectors_count": 0,
                "points_count": 0,
                "status": "unknown",
                "vector_size": None,
                "distance_metric": None,
                "segments_count": None,
                "hnsw_ef_construct": None,
                "hnsw_m": None,
                "shard_number": None,
                "replication_factor": None,
                "optimizer_status": None,
            }

    def count_by_type(self):
        """Count chunks by type."""
        counts = {}

        for chunk_type in ChunkType:
            try:
                result = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="type", match=MatchValue(value=chunk_type.value)
                            )
                        ]
                    ),
                )
                counts[chunk_type.value] = result.count
            except Exception as e:
                # logger.warning(f"Error counting {chunk_type}: {e}")
                print("Error counting", e)
                counts[chunk_type.value] = 0
        return counts

    def count_by_payload_types(self, payload_types: list[str]):
        """Count points by their payload `type` field for the given values."""
        counts: dict[str, int] = {}
        for payload_type in payload_types:
            try:
                result = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="type", match=MatchValue(value=payload_type)
                            )
                        ]
                    ),
                    exact=True,
                )
                counts[payload_type] = result.count
            except Exception as e:
                logger.info(
                    f"Error counting payload type '{payload_type}' in {self.collection_name}: {e}"
                )
                counts[payload_type] = 0
        return counts

    def count_schema_entity_types(self):
        """Count logical schema entities from TABLE_SCHEMA payload descriptions."""
        counts = {
            "table": 0,
            "column": 0,
            "relationship": 0,
            "foreignkey": 0,
            "example_query": 0,
        }

        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type", match=MatchValue(value="TABLE_SCHEMA")
                        )
                    ]
                ),
                limit=10_000,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                description = payload.get("description")
                if not description:
                    continue

                try:
                    content = json.loads(description)
                except Exception:
                    continue

                content_type = str(content.get("type", "")).upper()
                if content_type == "TABLE":
                    counts["table"] += 1
                elif content_type == "TABLE_COLUMNS":
                    for item in content.get("columns", []):
                        item_type = str(item.get("type", "")).upper()
                        if item_type == "COLUMN":
                            counts["column"] += 1
                        elif item_type == "FOREIGN_KEY":
                            counts["foreignkey"] += 1
                elif content_type == "RELATIONSHIP":
                    counts["relationship"] += 1
                elif content_type == "EXAMPLE_QUERY":
                    counts["example_query"] += 1
        except Exception as e:
            logger.info(
                f"Error counting schema entity types in {self.collection_name}: {e}"
            )

        return counts

    def get_columns_for_tables(
        self, table_names: list[str], schema_name: str = "public", limit: int = 100
    ):
        """
        Retrieve column chunks for specific table names without requiring a query vector.
        Uses Qdrant's scroll API for exact filtering.
        """
        must_conditions = [
            models.FieldCondition(
                key="type", match=models.MatchValue(value=ChunkType.COLUMN.value)
            ),
            models.FieldCondition(
                key="table_name", match=models.MatchAny(any=table_names)
            ),
            models.FieldCondition(
                key="schema_name", match=models.MatchValue(value=schema_name)
            ),
        ]
        search_filter = Filter(must=must_conditions)

        # Use scroll to retrieve points matching the filter (no vector needed)
        scroll_result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=search_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        retrieval_results = []
        for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
            metadata = ChunkMetadata(**point.payload)
            retrieval_result = RetrievalResult(
                chunk_id=str(point.id),
                chunk_type=ChunkType(metadata.type),
                content=metadata.description,
                metadata=metadata,
                score=1.0,  # No similarity score since no vector search
            )
            retrieval_results.append(retrieval_result)

        return retrieval_results
