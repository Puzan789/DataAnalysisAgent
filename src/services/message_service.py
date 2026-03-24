from src.database.models import Message, MessageEntry, Session, SessionStatus
import uuid
from datetime import datetime
from typing import Literal
from beanie.operators import And
from src.core.exception import NotFoundException
from loguru import logger


async def create_session(thread_id: uuid.UUID, user_id: str):
    """
    Create a new session with the given session_id.
    """

    session = await Session.find_one(Session.thread_id == thread_id)
    if not session:
        session = Session(
            thread_id=thread_id,
            user_id=user_id,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            chat_messages=[],
        )
        await session.insert()
    return session


async def add_message_separately(
    session: Session, message: str, role: Literal["user", "assistant"]
):
    new_message = Message(
        session_id=session.thread_id,
        messages=[MessageEntry(role=role, content=message)],
        timestamp=datetime.now(),
    )
    await new_message.insert()

    if session.message_ids is None:
        session.message_ids = []
        await session.insert()

    session.message_ids.append(new_message.id)
    session.updated_at = datetime.now()
    await session.save()


async def deactivate_session(thread_id: uuid.UUID) -> dict:
    session = await Session.find_one(Session.thread_id == thread_id)

    if not session:
        logger.error("Session not found")
        raise NotFoundException(message="Session not found")

    if session.status == SessionStatus.INACTIVE:
        return {
            "message": "Session is already inactive.",
        }

    session.status = SessionStatus.INACTIVE
    session.updated_at = datetime.now()
    await session.save()

    return {
        "message": "Session deactivated successfully.",
    }


async def get_session_messages(session: Session):
    """Retrieve all messages in a session."""
    messages = await Message.find(Message.session_id == session.thread_id).to_list()
    return messages


async def delete_session(user_id: str, session_id: uuid.UUID, checkpointer=None):
    """Delete the session and all associated messages for a specific user."""
    try:
        session = await Session.find_one(
            And(Session.thread_id == session_id, Session.user_id == user_id)
        )

        if not session:
            logger.error("Session not found or you don't have access to this session")
            raise NotFoundException(
                message="Session not found or you don't have access to this session"
            )

        if checkpointer:
            thread_id_str = str(session.thread_id)
            await checkpointer.adelete_thread(thread_id_str)
            logger.info(f"Deleted checkpoints for thread {thread_id_str}")

        await session.delete()

        messages = await get_session_messages(session)

        if not messages:
            logger.info("No messages in this session.")
            # raise NotFoundException(
            #     message="No messages in this session."
            # )
        else:
            for msg in messages:
                await msg.delete()

        return {"message": "Session and messages deleted successfully."}

    except NotFoundException:
        raise


async def get_threads_of_a_user(user_id: uuid.UUID):
    try:
        threads = await Session.find(Session.user_id == user_id).to_list()
        if not threads:
            raise NotFoundException(message="This user has no threads.")

        result = []
        for thread in threads:
            # Get the first user message as the thread title
            first_msg = await Message.find_one(Message.session_id == thread.thread_id)
            first_message = ""
            if first_msg and first_msg.messages:
                first_message = first_msg.messages[0].content

            result.append(
                {
                    "thread_id": str(thread.thread_id),
                    "title": first_message[:50] if first_message else None,
                    "first_message": first_message,
                    "created_at": thread.created_at.isoformat(),
                    "updated_at": thread.updated_at.isoformat(),
                }
            )

        # Sort by updated_at descending (most recent first)
        result.sort(key=lambda x: x["updated_at"], reverse=True)
        return result
    except NotFoundException:
        raise


async def get_messages_thread(user_id: uuid.UUID, thread_id: uuid.UUID):
    try:
        session = await Session.find_one(
            And(
                Session.thread_id == thread_id,
                Session.user_id == user_id,
            )
        )

        if not session:
            raise NotFoundException(message="No such thread found.")

        messages = await get_session_messages(session)

        # Flatten MessageEntry objects into {role, content} dicts
        flat = []
        for msg in messages:
            for entry in msg.messages:
                flat.append(
                    {
                        "role": entry.role,
                        "content": entry.content,
                    }
                )
        return flat

    except NotFoundException:
        raise
