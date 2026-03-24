from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from loguru import logger
from src.core.responses import APIResponse
from src.core.exception import CustomException
from src.core.auth import decode_token
from src.services.auth_service import register_user, authenticate_user, get_user_by_id


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


async def get_current_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise CustomException(message="Missing or invalid authorization header", status_code=401)
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise CustomException(message="Invalid or expired token", status_code=401)
    user = await get_user_by_id(payload.get("user_id"))
    if not user:
        raise CustomException(message="User not found", status_code=401)
    return user


@auth_router.post("/signup")
async def signup(body: SignupRequest):
    try:
        user, token = await register_user(body.email, body.password, body.name)
        return APIResponse(
            success=True,
            message="Signup successful",
            data={"token": token, "user": {"id": str(user.id), "email": user.email, "name": user.name}},
        )
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise


@auth_router.post("/login")
async def login(body: LoginRequest):
    try:
        user, token = await authenticate_user(body.email, body.password)
        return APIResponse(
            success=True,
            message="Login successful",
            data={"token": token, "user": {"id": str(user.id), "email": user.email, "name": user.name}},
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise


@auth_router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Current user",
        data={"id": str(current_user.id), "email": current_user.email, "name": current_user.name},
    )
