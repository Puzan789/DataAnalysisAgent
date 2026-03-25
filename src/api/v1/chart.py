import uuid
from fastapi import APIRouter, Request, BackgroundTasks, Depends, status
from pydantic import BaseModel
from loguru import logger

from src.api.v1.auth import get_current_user
from src.core.responses import APIResponse
from src.core.exception import CustomException, NotFoundException
from src.database.models import User

router = APIRouter(prefix="/charts", tags=["charts"])


class ChartRequest(BaseModel):
    query: str
    sql: str
    data: dict | None = None


class ChartAdjustmentRequest(BaseModel):
    query: str
    sql: str
    chart_schema: dict
    adjustment_option: dict
    data: dict | None = None




@router.post("", status_code=status.HTTP_200_OK)
async def create_chart(
    request: ChartRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Start chart generation as a background task. Returns query_id for polling."""
    try:
        query_id = str(uuid.uuid4())
        chart_service = req.app.state.services.chart_service

        background_tasks.add_task(
            chart_service.generate_chart,
            query_id=query_id,
            query=request.query,
            sql=request.sql,
            data=request.data,
        )

        logger.info(f"[ChartRouter] Started chart generation: {query_id}")
        return APIResponse(
            success=True,
            message="Chart generation started",
            data={"query_id": query_id},
        )
    except Exception as e:
        logger.error(f"Error starting chart generation: {e}")
        raise CustomException(message="Error starting chart generation")


@router.get("/{query_id}", status_code=status.HTTP_200_OK)
async def get_chart(
    query_id: str,
    req: Request,
    current_user: User = Depends(get_current_user),
):
    """Poll for chart generation result."""
    try:
        chart_service = req.app.state.services.chart_service
        result = chart_service.get_result(query_id)

        if result is None:
            raise NotFoundException(message="Chart query not found")

        return APIResponse(
            success=True,
            message="Chart result retrieved",
            data=result.model_dump(),
        )
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chart result: {e}")
        raise CustomException(message="Error retrieving chart result")


@router.patch("/{query_id}", status_code=status.HTTP_200_OK)
async def stop_chart(
    query_id: str,
    req: Request,
    current_user: User = Depends(get_current_user),
):
    """Stop a running chart generation."""
    try:
        chart_service = req.app.state.services.chart_service
        stopped = chart_service.stop(query_id)

        if not stopped:
            raise NotFoundException(message="Chart query not found")

        return APIResponse(success=True, message="Chart generation stopped")
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error stopping chart generation: {e}")
        raise CustomException(message="Error stopping chart generation")



@router.post("/adjustments", status_code=status.HTTP_200_OK)
async def create_chart_adjustment(
    request: ChartAdjustmentRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Start chart adjustment as a background task."""
    try:
        query_id = str(uuid.uuid4())
        chart_service = req.app.state.services.chart_service

        background_tasks.add_task(
            chart_service.adjust_chart,
            query_id=query_id,
            query=request.query,
            sql=request.sql,
            chart_schema=request.chart_schema,
            adjustment_option=request.adjustment_option,
            data=request.data,
        )

        logger.info(f"[ChartRouter] Started chart adjustment: {query_id}")
        return APIResponse(
            success=True,
            message="Chart adjustment started",
            data={"query_id": query_id},
        )
    except Exception as e:
        logger.error(f"Error starting chart adjustment: {e}")
        raise CustomException(message="Error starting chart adjustment")


@router.get("/adjustments/{query_id}", status_code=status.HTTP_200_OK)
async def get_chart_adjustment(
    query_id: str,
    req: Request,
    current_user: User = Depends(get_current_user),
):
    """Poll for chart adjustment result."""
    try:
        chart_service = req.app.state.services.chart_service
        result = chart_service.get_result(query_id)

        if result is None:
            raise NotFoundException(message="Chart adjustment not found")

        return APIResponse(
            success=True,
            message="Chart adjustment result retrieved",
            data=result.model_dump(),
        )
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chart adjustment result: {e}")
        raise CustomException(message="Error retrieving chart adjustment result")
