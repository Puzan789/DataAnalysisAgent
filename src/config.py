from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    QDRANT_URL: str | None = None
    langsmith_tracing: bool = False
    langsmith_endpoint: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    OPENAI_KEY: str | None = None
    OPENAI_MODEL: str | None = None
    EMBEDDING_MODEL: str | None = None

    # MongoDB
    MONGO_DB_URI: str
    MONGO_DB_NAME: str = "data_analysis"

    # PostgreSQL
    POSTGRES_USERNAME: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "host.docker.internal"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mydb"

    # Schema collection name = "postgres"
    TABLE_DESCRIPTION_COLLECTION: str
    DB_SCHEMA_COLLECTION: str
    COMPANY_COLLECTION: str

    # Auth
    AUTH_SECRET: str 
    AUTH_TOKEN_EXP_MIN: int = 1440

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def all_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Debugging
    DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
