from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    username: str
    role: str = "user"
    created_at: Optional[datetime] = None


class BaseAuthProvider(ABC):
    """Abstract base class for extensible authentication providers."""

    name: str = "base"

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with given credentials (e.g. username/password, token)."""
        pass

    @abstractmethod
    def create_token(self, user: User) -> str:
        """Create a signed session token for an authenticated user."""
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[User]:
        """Verify session token and return the User if valid, None otherwise."""
        pass
