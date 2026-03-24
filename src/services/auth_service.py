from datetime import datetime
from pydantic import EmailStr
from src.database.models import User
from uuid import UUID
from src.core.auth import hash_password, verify_password, create_token
from src.core.exception import CustomException


async def register_user(email: EmailStr, password: str, name: str | None = None):
    existing = await User.find_one(User.email == email)
    if existing:
        raise CustomException(message="User already exists")
    pwd_hash = hash_password(password)
    user = User(
        email=email, password_hash=pwd_hash, name=name, created_at=datetime.utcnow()
    )
    await user.create()
    token = create_token({"user_id": str(user.id), "email": user.email})
    return user, token


async def authenticate_user(email: EmailStr, password: str):
    user = await User.find_one(User.email == email)
    if not user or not verify_password(password, user.password_hash):
        raise CustomException(message="Invalid credentials")
    token = create_token({"user_id": str(user.id), "email": user.email})
    return user, token


async def get_user_by_id(user_id: str) -> User | None:
    try:
        uid = UUID(str(user_id))
        return await User.get(uid)
    except Exception:
        return None
