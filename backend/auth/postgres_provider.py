import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

from backend.auth.base import BaseAuthProvider, User
from backend.db.postgres import UserRecord, get_session, hash_password, verify_password

logger = logging.getLogger(__name__)


class PostgresAuthProvider(BaseAuthProvider):
    """Database-backed authentication provider using PostgreSQL (or SQLite fallback)."""

    name = "postgres"

    def __init__(self, secret_key: Optional[str] = None, token_expire_hours: Optional[int] = None):
        self.secret_key = secret_key or os.getenv("AUTH_JWT_SECRET", "super-secret-jwt-signing-key-replace-in-prod")
        self.expire_seconds = int(token_expire_hours or os.getenv("AUTH_TOKEN_EXPIRE_HOURS", 72)) * 3600

    def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        username = credentials.get("username") or credentials.get("id")
        password = credentials.get("password") or credentials.get("pass")

        if not username or not password:
            return None

        session = get_session()
        try:
            record = session.query(UserRecord).filter(UserRecord.username == username.strip()).first()
            if not record:
                logger.warning(f"Authentication failed: user '{username}' not found.")
                return None

            if not verify_password(password, record.password_hash):
                logger.warning(f"Authentication failed: invalid password for user '{username}'.")
                return None

            return User(
                id=record.id,
                username=record.username,
                role=record.role,
                created_at=record.created_at,
            )
        finally:
            session.close()

    def register_user(self, username: str, password: str, role: str = "user") -> User:
        username = username.strip()
        if not username or not password:
            raise ValueError("Username and password are required.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        session = get_session()
        try:
            existing = session.query(UserRecord).filter(UserRecord.username == username).first()
            if existing:
                raise ValueError(f"Username '{username}' already exists.")

            new_user = UserRecord(
                id=str(uuid.uuid4()),
                username=username,
                password_hash=hash_password(password),
                role=role,
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            return User(
                id=new_user.id,
                username=new_user.username,
                role=new_user.role,
                created_at=new_user.created_at,
            )
        finally:
            session.close()

    def create_token(self, user: User) -> str:
        """Create an HMAC-SHA256 signed session token."""
        exp = int(time.time()) + self.expire_seconds
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": exp,
            "provider": self.name,
        }
        raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8").rstrip("=")
        sig = hmac.new(self.secret_key.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64_payload}.{sig}"

    def verify_token(self, token: str) -> Optional[User]:
        """Verify an HMAC-SHA256 signed session token."""
        try:
            parts = token.strip().split(".")
            if len(parts) != 2:
                return None
            b64_payload, signature = parts[0], parts[1]

            # Re-pad base64
            padding = 4 - (len(b64_payload) % 4)
            if padding != 4:
                b64_payload_padded = b64_payload + ("=" * padding)
            else:
                b64_payload_padded = b64_payload

            expected_sig = hmac.new(self.secret_key.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                logger.warning("Token verification failed: invalid signature.")
                return None

            payload = json.loads(base64.urlsafe_b64decode(b64_payload_padded).decode("utf-8"))
            if payload.get("exp", 0) < time.time():
                logger.warning("Token verification failed: token expired.")
                return None

            user_id = payload.get("sub")
            username = payload.get("username")

            # Check if user still exists in database
            session = get_session()
            try:
                record = session.query(UserRecord).filter(UserRecord.id == user_id).first()
                if not record:
                    return None
                return User(
                    id=record.id,
                    username=record.username,
                    role=record.role,
                    created_at=record.created_at,
                )
            finally:
                session.close()

        except Exception as exc:
            logger.warning(f"Token verification error: {exc}")
            return None
