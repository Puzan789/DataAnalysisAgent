import uuid
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from src.globals import ServiceContainer, get_service_container
from src.web.v1.services.schema_extraction import SchemaExtractionService

router = APIRouter()


@router.post("/extract-schema")
async def extract_schema(
    request: SchemaExtractionService.Request,
    background_tasks: BackgroundTasks,
    service_container: ServiceContainer = Depends(get_service_container),
) -> SchemaExtractionService.Response:
    extraction_id = str(uuid.uuid4())
    service_container.schema_extraction_service._extraction_statuses[extraction_id] = (
        SchemaExtractionService.StatusResponse(status="extracting")
    )
    background_tasks.add_task(
        service_container.schema_extraction_service.extract_schema,
        request,
        extraction_id,
        # service_metadata=asdict(service_container),
    )
    return SchemaExtractionService.Response(success=True, id=extraction_id)


@router.get("/schema-extractions/{extraction_id}/result")
async def get_extraction_result(
    extraction_id: str,
    service_container: ServiceContainer = Depends(get_service_container),
) -> SchemaExtractionService.StatusResponse:
    """
    Get status and result of schema extraction.

    Poll this endpoint to check if extraction is complete.

    Status values:
    - "extracting": Still processing
    - "finished": Complete, MDL available in response
    - "failed": Error occurred, check error field

    Example:
        GET /v1/schema-extractions/550e8400-e29b-41d4-a716-446655440000/result

        Response (in progress):
        {
            "status": "extracting",
            "mdl": null,
            "error": null
        }

        Response (complete):
        {
            "status": "finished",
            "mdl": {
                "models": [...],
                "relationships": [...]
            },
            "error": null
        }
    """
    return service_container.schema_extraction_service.get_extraction_status(
        extraction_id
    )
