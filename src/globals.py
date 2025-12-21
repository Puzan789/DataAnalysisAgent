from dataclasses import asdict, dataclass
from src.web.v1 import services
from src.core.pipeline import PipelineComponent
from src.config import Settings


@dataclass
class ServiceContainer:
    schema_extraction_service: services.SchemaExtractionService


def create_service_container(
    # pipe_components: dict[str, PipelineComponent],
    settings: Settings,
) -> ServiceContainer:
    query_cache = {
        "maxsize": settings.query_cache_maxsize,
        "ttl": settings.query_cache_ttl,
    }
    return ServiceContainer(
        schema_extraction_service=services.SchemaExtractionService(
            **query_cache,
        )
    )

    # return ServiceContainer(schema_extraction_service=services.SchemaExtractionService(
    #     pipelines={
    #         "db_schema":indexing.DBSchema        }

    # )


## do now indexing from dbschema


# TODO
# add the schema extraction only and see the output


def get_service_container():
    from src.__main__ import app

    return app.state.service_container



    # def _build_connection_url(self) -> str:
    #     """Build PostgreSQL connection URL."""
    #     return (
    #         f"postgresql+asyncpg://{self._settings.POSTGRES_USERNAME}:"
    #         f"{self._settings.POSTGRES_PASSWORD}@{self._settings.POSTGRES_HOST}:"
    #         f"{self._settings.POSTGRES_PORT}/{self._settings.POSTGRES_DB}"
    #     )