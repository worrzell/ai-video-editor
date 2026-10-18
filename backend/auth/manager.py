import logging
from typing import Any, Dict, Optional, Tuple

from backend.auth.base import BaseAuthProvider, User
from backend.auth.postgres_provider import PostgresAuthProvider

logger = logging.getLogger(__name__)


class AuthManager:
    """Central manager orchestrating pluggable authentication providers."""

    def __init__(self):
        self._providers: Dict[str, BaseAuthProvider] = {}
        self._default_provider_name: str = "postgres"

    def register_provider(self, provider: BaseAuthProvider, is_default: bool = False) -> None:
        """Register an authentication provider."""
        self._providers[provider.name] = provider
        if is_default or len(self._providers) == 1:
            self._default_provider_name = provider.name
        logger.info(f"Registered auth provider: '{provider.name}'")

    def get_provider(self, name: Optional[str] = None) -> BaseAuthProvider:
        """Get provider by name, or the default provider."""
        provider_name = name or self._default_provider_name
        if provider_name not in self._providers:
            raise KeyError(f"Auth provider '{provider_name}' not found. Registered: {list(self._providers.keys())}")
        return self._providers[provider_name]

    def authenticate(
        self, credentials: Dict[str, Any], provider_name: Optional[str] = None
    ) -> Tuple[User, str]:
        """Authenticate user against specified (or default) provider and return (User, token)."""
        provider = self.get_provider(provider_name)
        user = provider.authenticate(credentials)
        if not user:
            raise ValueError("Invalid username or password.")
        token = provider.create_token(user)
        return user, token

    def verify_token(self, token: str) -> Optional[User]:
        """Verify token across registered providers."""
        if not token:
            return None

        # Try providers in order
        for provider in self._providers.values():
            user = provider.verify_token(token)
            if user:
                return user

        return None


_auth_manager_instance: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or initialize singleton AuthManager."""
    global _auth_manager_instance
    if _auth_manager_instance is None:
        mgr = AuthManager()
        # Register default Postgres / DB provider
        postgres_provider = PostgresAuthProvider()
        mgr.register_provider(postgres_provider, is_default=True)
        _auth_manager_instance = mgr
    return _auth_manager_instance
