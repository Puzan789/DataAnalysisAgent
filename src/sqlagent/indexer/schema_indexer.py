from src.config import settings
from src.sqlagent.embeddings.vectorstore import VectorStore
from src.sqlagent.ingestion.schema_extractor import SchemaExtractor
from src.sqlagent.ingestion.chunk_generator import ChunkGenerator
from src.sqlagent.embeddings.embedder import OpenAIEmbedder
from loguru import logger


class SchemaIndexer:
    """Class for indexing database schema information."""

    def __init__(self):
        self.embedding_model = OpenAIEmbedder(settings.EMBEDDING_MODEL)
        self.table_descriptions_store = VectorStore(
            settings.TABLE_DESCRIPTION_COLLECTION
        )
        self.db_schema_store = VectorStore(settings.DB_SCHEMA_COLLECTION)

    def init_schema(self):
        """Initilialize and index database schema information."""
        self.table_descriptions_store.create_collection()
        self.db_schema_store.create_collection()

        extractor = SchemaExtractor()
        all_tables = extractor.extract_all_tables()
        chunk_gen = ChunkGenerator()

        # Table descriptions for the vector store
        description_chunks = []
        description_metadata = []
        for table_info in all_tables:
            table_chunk = chunk_gen.generate_table_chunk(table_info)
            description_chunks.append(table_chunk.to_text())
            description_metadata.append(
                {
                    "type": "TABLE_DESCRIPTION",
                    "table_name": table_chunk.table_name,
                    "description": table_chunk.to_text(),
                }
            )

        # Embed and store table descriptions
        description_embeddings = self.embedding_model.embed_texts(description_chunks)
        logger.info(
            f"Generated {len(description_embeddings)} embeddings for {len(description_chunks)} table descriptions."
        )
        self.table_descriptions_store.upsert_chunks(
            description_embeddings, description_metadata
        )
        # Embed and store db schemas
        schema_chunks = []
        schema_metadata = []

        technical_docs = chunk_gen.generate_db_schema_chunks(extractor)
        for doc in technical_docs:
            schema_chunks.append(doc.page_content)  # JSON string
            schema_metadata.append(
                {
                    "type": "TABLE_SCHEMA",
                    "table_name": doc.metadata["name"],
                    "description": doc.page_content,
                }
            )

        schema_embeddings = self.embedding_model.embed_texts(schema_chunks)
        logger.info(
            f"Generated {len(schema_embeddings)} embeddings for {len(schema_chunks)} database schemas."
        )
        self.db_schema_store.upsert_chunks(schema_embeddings, schema_metadata)
        return {
            "descriptions": (description_chunks, description_metadata),
            "schemas": (schema_chunks, schema_metadata),
        }
