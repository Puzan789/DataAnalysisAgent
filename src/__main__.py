import uvicorn
from fastapi import FastAPI
from src.globals import create_service_container
from contextlib import asynccontextmanager
from src.web.v1.routers import schema_extraction_router
from src.config import settings
# from src.providers import generate_components this is not used currently


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # pipe_components = generate_components(settings.components)
    app.state.service_container = create_service_container(settings=settings)
    yield
    # Cleanup logic can be added here if needed


app = FastAPI(lifespan=lifespan)

app.include_router(schema_extraction_router, prefix="/v1/schema-extractions")

# if __name__ == "__main__":
#     uvicorn.run(
#         "src.__main__:app",
#         host=settings.host,
#         port=settings.port,
#         reload=settings.development,
#         reload_includes=["src/**/*.py", ".env.dev", "config.yaml"],
#         reload_excludes=["tests/**/*.py", "eval/**/*.py"],
#         workers=1,
#         loop="uvloop",
#         http="httptools",
#     )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.__main__:app",  # module path to your FastAPI app
        host="0.0.0.0",  # listen on all network interfaces
        port=8000,  # the port number
        reload=True,  # auto-reload for development
    )
