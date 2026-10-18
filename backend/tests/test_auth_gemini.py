import json
import os
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient

from backend.auth import User, get_auth_manager
from backend.auth.postgres_provider import PostgresAuthProvider
from backend.db.postgres import (
    RenderJobRecord,
    UserRecord,
    get_session,
    hash_password,
    init_postgres,
    verify_password,
)
from backend.services.planner import call_gemini_api, plan_edit
from backend.api.server import app


def test_password_hashing():
    raw = "my_secret_password_123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    print("✓ Password hashing & verification verified.")


def test_auth_manager_and_provider():
    init_postgres()
    mgr = get_auth_manager()

    # Authenticate seeded admin
    user, token = mgr.authenticate({"username": "admin", "password": "editor_admin_2026"})
    assert user.username == "admin"
    assert token is not None

    # Verify token
    verified = mgr.verify_token(token)
    assert verified is not None
    assert verified.id == user.id
    assert verified.username == "admin"

    # Register new user
    provider = mgr.get_provider("postgres")
    test_user = f"test_{os.urandom(4).hex()}"
    new_user = provider.register_user(test_user, "password_12345")
    assert new_user.username == test_user

    # Login with new user
    auth_user, auth_token = mgr.authenticate({"username": test_user, "password": "password_12345"})
    assert auth_user.username == test_user

    print("✓ AuthManager & PostgresAuthProvider operations verified.")


def test_api_server_endpoints():
    client = TestClient(app)

    # 1. Unauthenticated me
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["authenticated"] is False

    # 2. Protected endpoint without cookie returns 401
    res = client.post("/api/render", data={"prompt": "Test edit"})
    assert res.status_code == 401

    # 3. Login returns cookie
    res = client.post("/api/auth/login", json={"username": "admin", "password": "editor_admin_2026"})
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert res.json()["status"] == "success"

    # 4. Authenticated me with cookie
    res = client.get("/api/auth/me", cookies=res.cookies)
    assert res.status_code == 200
    assert res.json()["authenticated"] is True
    assert res.json()["user"]["username"] == "admin"

    # 5. Logout clears cookie
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    print("✓ FastAPI cookie authentication endpoints verified.")


def test_chunked_upload():
    from backend.api.server import app, CLIPS_DIR
    import io

    client = TestClient(app)
    # Login as admin to get token
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "editor_admin_2026"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Prepare 3 chunks of a test video
    chunk_1 = b"AAAA" * 1024
    chunk_2 = b"BBBB" * 1024
    chunk_3 = b"CCCC" * 1024
    full_content = chunk_1 + chunk_2 + chunk_3
    test_filename = "test_chunked_video.mp4"

    # Send chunk 0
    res = client.post(
        "/api/upload/chunk",
        headers=headers,
        data={"filename": test_filename, "chunk_index": 0, "total_chunks": 3},
        files={"file": (test_filename, io.BytesIO(chunk_1), "video/mp4")},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "chunk_received"

    # Send chunk 1
    res = client.post(
        "/api/upload/chunk",
        headers=headers,
        data={"filename": test_filename, "chunk_index": 1, "total_chunks": 3},
        files={"file": (test_filename, io.BytesIO(chunk_2), "video/mp4")},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "chunk_received"

    # Send chunk 2 (final)
    res = client.post(
        "/api/upload/chunk",
        headers=headers,
        data={"filename": test_filename, "chunk_index": 2, "total_chunks": 3},
        files={"file": (test_filename, io.BytesIO(chunk_3), "video/mp4")},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "complete"
    assert res.json()["filename"] == test_filename

    # Verify file assembled properly on disk
    dest = CLIPS_DIR / test_filename
    assert dest.exists()
    assert dest.read_bytes() == full_content
    # Clean up test file
    dest.unlink(missing_ok=True)
    print("✓ Chunked upload reassembly verified byte-for-byte.")


def test_gemini_planner_execution():
    segments = [
        {"clip_id": "clip1.mp4", "start": 0.0, "end": 5.0, "text": "Dramatic opening scene with fast cuts."},
        {"clip_id": "clip2.mp4", "start": 10.0, "end": 14.5, "text": "High action climax and thrilling music."},
    ]
    plan = plan_edit("Create an exciting trailer", segments)
    assert len(plan.timeline) > 0
    assert plan.style.aspect_ratio in ["16:9", "9:16", "1:1"]
    assert plan.style.pace in ["slow", "normal", "fast"]
    print(f"✓ Gemini 3.8 Flash returned valid EditPlan with {len(plan.timeline)} timeline items.")


if __name__ == "__main__":
    print("\nRunning test suite...")
    test_password_hashing()
    test_auth_manager_and_provider()
    test_api_server_endpoints()
    test_gemini_planner_execution()
    print("\n✓ ALL TESTS PASSED SUCCESSFULLY!")
