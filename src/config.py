from sys import settrace
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # # Database settings
    # POSTGRES_USERNAME: str | None = None
    # POSTGRES_PASSWORD: str | None = None
    # POSTGRES_HOST: str | None = None
    # POSTGRES_PORT: str | None = None
    # POSTGRES_DB: str | None = None
    # POSTGRES_SSL_MODE: str = "require"

    # @property
    # def database_url(self) -> str | None:
    #     """Build PostgreSQL connection URL."""
    #     if not all(
    #         [
    #             self.POSTGRES_USERNAME,
    #             self.POSTGRES_PASSWORD,
    #             self.POSTGRES_HOST,
    #             self.POSTGRES_PORT,
    #             self.POSTGRES_DB,
    #         ]
    #     ):
    #         return None
    #     return (
    #         f"postgresql://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}"
    #         f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    #         f"?sslmode={self.POSTGRES_SSL_MODE}"
    #     )

    # Caching settings
    query_cache_ttl: int = Field(default=3600)  # unit: seconds
    query_cache_maxsize: int = Field(
        default=1_000_000,
    )


settings = Settings()
