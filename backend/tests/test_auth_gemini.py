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
    # Next me is unauthenticated
    res = client.get("/api/auth/me")
    assert res.json()["authenticated"] is False

    print("✓ FastAPI cookie authentication endpoints verified.")


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
