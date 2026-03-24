from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from src.database.state import create_database_state
from src.core.exception import register_exception_handlers
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from src.api import router as v1_router
from src.config import settings
from fastapi.middleware.cors import CORSMiddleware
import traceback
from src.core.container import create_service_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    db_state = create_database_state(settings)
    try:
        logger.info("Starting database connections...")
        await db_state.connect_all()
        logger.info("Database connections established.")

        db_state.checkpointer = AsyncMongoDBSaver(
            client=db_state.mongo.get_client(),
        )

        logger.info("Creating service container...")
        container = await create_service_container(db_state)
        logger.info("All database connections established.")
        app.state.db = db_state
        app.state.services = container
        from src.database.state import set_global_db_state

        set_global_db_state(db_state)
        logger.info("Application startup complete!")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        await db_state.disconnect_all()
        logger.info("All database connections closed.")


app = FastAPI(
    title="Data Analysis Agent",
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.get("/health")
async def health_check():
    """Simple health check for load balancers/K8s"""
    return {"status": "healthy"}


@app.get("/health/db")
async def health_check_db():
    """Detailed health check including database connections"""
    try:
        db_state = app.state.db
        db_health = await db_state.health_check()
        return {
            "status": "healthy" if all(db_health.values()) else "unhealthy",
            "databases": db_health,
        }
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "databases": {}}


app.include_router(v1_router, prefix="/api/v1")

logger.info("API is running...")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7000,
        reload=True,
    )
