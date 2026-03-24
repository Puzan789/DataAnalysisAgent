from fastapi import HTTPException, status, Request, FastAPI
from fastapi.responses import JSONResponse
from http import HTTPStatus


class CustomException(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message: str | None = None,
        success: bool = False,
    ) -> None:
        if not message:
            message = HTTPStatus(status_code).description
        self.success = success
        super().__init__(status_code=status_code, detail=message)


class FailedException(CustomException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            success=False,
        )


class NotFoundException(CustomException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, message=message, success=False
        )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": exc.success,
                "message": exc.detail,
                "data": None,
            },
        )
