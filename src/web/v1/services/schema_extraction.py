import json
from typing import Any, Literal, Optional
from loguru import logger
from pydantic import BaseModel
from src.core.pipeline import BasicPipeline
from cachetools import TTLCache
from src.extractors.extractor_json import JsonExtractor


class SchemaExtractionService:
    """Extract database schema and index to Qdrant vector database"""

    class Request(BaseModel):
        """Schema extraction request model."""

        database_url: Optional[str] = None
        file_content: Optional[bytes] = None
        file_extension: Optional[str] = None
        schema: str = "public"
        project_id: str

    class Response(BaseModel):
        """Schema extraction response model."""

        success: bool
        id: str

    class StatusResponse(BaseModel):
        """Schema extraction status response model."""

        status: Literal["extracting", "completed", "failed"]
        jsons: Optional[dict[str, Any]] = None
        error: Optional["SchemaExtractionService.Error"] = None

    class Error(BaseModel):
        """Error detail"""

        code: str
        message: str

    def __init__(
        self,
        # pipelines: dict[str, BasicPipeline],
        maxsize: int = 1_000_000,
        ttl: int = 120,
    ):
        # self.db_schema_pipeline = pipelines.get("db_schema") #1
        # if not self.db_schema_pipeline:
        #     raise ValueError("db_schema pipeline is required") #3
        # TTl cache for tracking extraction status
        self._extraction_statuses: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        logger.info("SchemaExtractionService initialized")

    # add  @observe(name=ExtractSchema)
    # @trace_metadata
    async def extract_schema(
        self, request: Request, extraction_id: str, **kwargs
    ) -> None:
        """Extract schema from database or file and index to Qdrant vector database"""
        # set initial input
        self._extraction_statuses[extraction_id] = self.StatusResponse(
            status="extracting"
        )
        try:
            logger.info(f"Starting schema extraction for Project: {request.project_id}")
            extractor = JsonExtractor.from_connection_string(
                request.database_url, schema=request.schema
            )
            jsons = (
                await extractor.extract_json()
            )  # project_id=request.project_id (add )
            logger.info("Extracted JSON schema")
            json_str = json.dumps(jsons)
            # run pipeline to index to Qdrant
            # await self.db_schema_pipeline.run(json_str, project_id=request.project_id) #2
            logger.info("Indexed schema to Qdrant")
            self._extraction_statuses[extraction_id] = self.StatusResponse(
                status="completed", jsons=jsons
            )
            return json_str
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            self._extraction_statuses[extraction_id] = self.StatusResponse(
                status="failed",
                error=self.Error(code="extraction_failed", message=str(e)),
            )

    def get_extraction_status(self, extraction_id: str) -> StatusResponse:
        """Get the status of a schema extraction."""
        return self._extraction_statuses.get(
            extraction_id,
            self.StatusResponse(
                status="failed",
                error=self.Error(code="not_found", message="Extraction ID not found."),
            ),
        )


#  def _build_connection_url(self) -> str:
#         """Build PostgreSQL connection URL."""
#         if self.db_type == "postgresql":
#             return (
#                 f"postgresql+asyncpg://{self.username}:"
#                 f"{self._settings.POSTGRES_PASSWORD}@{self._settings.POSTGRES_HOST}:"
#                 f"{self._settings.POSTGRES_PORT}/{self._settings.POSTGRES_DB}"
#             )
