from fastapi import APIRouter, Query
from src.core.responses import APIResponse
from src.core.exception import CustomException
from src.services.database_service import (
    get_database_overview as _get_overview,
    get_all_tables as _get_tables,
    get_table_schema as _get_schema,
    get_table_data as _get_data,
    get_all_relationships as _get_relationships,
)
from loguru import logger

router = APIRouter(prefix="/db", tags=["Database Explorer"])


@router.get("/overview")
async def get_database_overview():
    try:
        data = await _get_overview()
        return APIResponse(success=True, message="Database overview", data=data)
    except Exception as e:
        logger.error(f"Error getting database overview: {e}")
        raise CustomException(message="Error getting database overview")


@router.get("/tables")
async def get_tables():
    try:
        data = await _get_tables()
        return APIResponse(success=True, message="Tables retrieved", data=data)
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise CustomException(message="Error listing tables")


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str):
    try:
        data = await _get_schema(table_name)
        return APIResponse(success=True, message=f"Schema for {table_name}", data=data)
    except Exception as e:
        logger.error(f"Error getting schema for {table_name}: {e}")
        raise CustomException(message=f"Error getting schema for {table_name}")


@router.get("/tables/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    try:
        data = await _get_data(table_name, page, page_size)
        return APIResponse(success=True, message=f"Data from {table_name}", data=data)
    except Exception as e:
        logger.error(f"Error getting data for {table_name}: {e}")
        raise CustomException(message=f"Error getting data for {table_name}")


@router.get("/relationships")
async def get_relationships():
    try:
        data = await _get_relationships()
        return APIResponse(success=True, message="Relationships retrieved", data=data)
    except Exception as e:
        logger.error(f"Error getting relationships: {e}")
        raise CustomException(message="Error getting relationships")
