from src.core.pipeline import BasicPipeline
from src.core.provider import EmbedderProvider, DocumentStoreProvider
from hamilton.async_driver import AsyncDriver
from typing import Any, Optional
from langchain_core.documents import Document
import uuid
import tqdm


class DDLChunker:
    async def run(
        self, jsons: dict[str, Any], column_size: int, project_id: Optional[str] = None
    ):
        chunks = [
            {
                id: str(uuid.uuid4()),
                "meta": {
                    "type": "TABLE_SCHEMA",
                    "name": chunk["name"],
                    **({"project_id": project_id} if project_id else {}),
                },
            }
            for chunk in await self._get_ddl_commands(**jsons, column_size=column_size)
        ]

        return {
            "documents": [
                Document(**chunk)
                for chunk in tqdm(
                    chunks, desc="DDL chunking into docuemnts for {project_id}"
                )
            ]
        }

    async def _get_ddl_commands(
        self,
        models: list,
        relationships: list,
        views: list,
        metrics: list,
        column_size: int = 50,
        **kwargs,
    ) -> list[dict]:
        return self._convert_models_and_relationships()

    def _convert_models_and_relationships(self):
        pass


class DBSchema(BasicPipeline):
    def __init__(
        self,
        embedder_provider: EmbedderProvider,
        document_store_provider: DocumentStoreProvider,
        **kwargs,
    ) -> None:
        db_schema_store = document_store_provider.get_store()
        self._components = {}
