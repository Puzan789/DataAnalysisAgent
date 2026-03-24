from typing import Literal
from beanie import Document, PydanticObjectId
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID, uuid4
from enum import Enum


class MessageEntry(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message content")


class Message(Document):
    session_id: UUID = Field(..., description="Associated session ID")
    messages: list[MessageEntry] = Field(..., description="Chat message list")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "chat_messages"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Session(Document):
    user_id: UUID = Field(..., description="ID of the user owning the session")
    thread_id: UUID = Field(..., description="Thread ID to group chat messages")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    message_ids: list[PydanticObjectId] = Field(
        default_factory=list, description="List of message document IDs"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "sessions"


class User(Document):
    id: UUID | None = Field(default_factory=uuid4)
    email: EmailStr = Field(..., description="User email", unique=True)
    password_hash: str = Field(..., description="Hashed password")
    name: str | None = Field(default=None, description="Display name")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
