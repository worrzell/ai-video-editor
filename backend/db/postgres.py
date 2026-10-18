import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import (
    Column,
    DateTime,
    JSON,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserRecord(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RenderJobRecord(Base):
    __tablename__ = "render_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)
    prompt = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="completed")
    edit_plan = Column(JSON, nullable=True)
    output_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_bytes(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against salt$hash string."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_hash = bytes.fromhex(parts[1])
        actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False


_engine = None
_session_factory = None
_active_db_type = "unknown"


def get_default_db_url() -> str:
    """Get database URL from environment or construct unix-socket connection for PostgreSQL."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Check unix domain socket for postgres
    if os.path.exists("/var/run/postgresql"):
        user = os.getenv("USER", "worrzell")
        return f"postgresql://{user}@/ai_video_editor?host=/var/run/postgresql"

    return "postgresql://localhost:5432/ai_video_editor"


def init_postgres(db_url: Optional[str] = None):
    """Initialize database engine, create tables, and seed admin user."""
    global _engine, _session_factory, _active_db_type

    url = db_url or get_default_db_url()
    logger.info(f"Connecting to database: {url.split('@')[-1] if '@' in url else url}")

    try:
        engine = create_engine(url, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        _engine = engine
        _session_factory = sessionmaker(bind=_engine)
        _active_db_type = "postgresql" if "postgres" in url else "sqlite"
        logger.info(f"Database ({_active_db_type}) initialized successfully.")
    except Exception as exc:
        logger.warning(
            f"Failed to connect to primary database ({exc}). "
            "To grant full PostgreSQL access, run:\n"
            "  sudo -u postgres createdb -O worrzell ai_video_editor\n"
            "Falling back to local SQLite database..."
        )
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{data_dir / 'app.db'}"
        _engine = create_engine(sqlite_url, pool_pre_ping=True)
        Base.metadata.create_all(_engine)
        _session_factory = sessionmaker(bind=_engine)
        _active_db_type = "sqlite"
        logger.info(f"Fallback SQLite database initialized at {sqlite_url}.")

    # Seed initial admin user if empty
    session = _session_factory()
    try:
        if session.query(UserRecord).count() == 0:
            default_user = os.getenv("AUTH_DEFAULT_USER", "admin")
            default_pass = os.getenv("AUTH_DEFAULT_PASS", "editor_admin_2026")
            admin_user = UserRecord(
                id=str(uuid.uuid4()),
                username=default_user,
                password_hash=hash_password(default_pass),
                role="admin",
            )
            session.add(admin_user)
            session.commit()
            logger.info(f"Seeded initial admin user: '{default_user}'")
    except Exception as exc:
        session.rollback()
        logger.error(f"Error checking/seeding admin user: {exc}")
    finally:
        session.close()

    return _engine


def get_session():
    """Get a new SQLAlchemy session."""
    global _session_factory
    if _session_factory is None:
        init_postgres()
    return _session_factory()


def get_active_db_type() -> str:
    """Return active database engine type ('postgresql' or 'sqlite')."""
    return _active_db_type
