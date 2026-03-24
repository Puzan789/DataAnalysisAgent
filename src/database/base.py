from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseConnection(ABC):
    """Abstract base class for database connections"""

    @abstractmethod
    async def connect(self):
        """Establish the database connection."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close the database connection."""
        pass

    @abstractmethod
    async def health_check(self) -> AsyncSession:
        """Check connection health"""
        pass


class SessionProvider(ABC):
    """Abstract base class for session providers"""

    @abstractmethod
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        pass
