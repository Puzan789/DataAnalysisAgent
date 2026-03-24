from pydantic import BaseModel
from typing import Optional, TypeVar, Generic

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Everything is OK",
                "data": None,
                "error_code": 0,
            }
        }
    }
