import json
import logging
import os
import shutil
import uuid
import re
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi import status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.auth import User, get_auth_manager
from backend.auth.postgres_provider import PostgresAuthProvider
from backend.db.postgres import RenderJobRecord, get_active_db_type, get_session, init_postgres
from backend.models.edit_plan import EditPlan
from backend.services.embedding import EmbeddingProvider
from backend.services.executor import render_plan
from backend.services.indexing import build_index
from backend.services.ingestion import ingest_clips, save_manifest, scan_clips
from backend.services.planner import plan_edit
from backend.services.retrieval import retrieve_segments
from backend.services.transcription import transcribe_clips

logger = logging.getLogger('ai-video-editor')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
CLIPS_DIR = DATA_DIR / 'clips'
TRANSCRIPTS_DIR = DATA_DIR / 'transcripts'
OUTPUT_DIR = DATA_DIR / 'outputs'
OUTPUT_VIDEO = OUTPUT_DIR / 'final.mp4'
STATIC_DIR = Path(__file__).resolve().parent / 'static'

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv'}

app = FastAPI(title='AI Video Editor (Gemini + PostgreSQL)')

# Enable CORS for external frontends while supporting credentials (cookies/auth headers)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


def ensure_directories() -> None:
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def on_startup():
    ensure_directories()
    init_postgres()
    logger.info("Server startup complete. PostgreSQL & Gemini backend ready.")


# ---------------------------------------------------------
# Authentication Models & Dependencies
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str
    provider: Optional[str] = "postgres"


class RegisterRequest(BaseModel):
    username: str
    password: str


def get_current_user(request: Request) -> User:
    """Extract and verify session token from HttpOnly cookie, or Bearer/API-key header."""
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif request.headers.get("X-API-Key"):
            token = request.headers.get("X-API-Key").strip()

    if not token:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    auth_manager = get_auth_manager()
    user = auth_manager.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )
    return user


def get_optional_user(request: Request) -> Optional[User]:
    """Helper to get user if authenticated, without raising 401."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None


# ---------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------

@app.post("/api/auth/login")
def login(creds: LoginRequest) -> JSONResponse:
    auth_manager = get_auth_manager()
    try:
        user, token = auth_manager.authenticate(
            {"username": creds.username, "password": creds.password},
            provider_name=creds.provider
        )
        max_age = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "72")) * 3600
        json_resp = JSONResponse({
            "status": "success",
            "message": f"Welcome back, {user.username}!",
            "token": token,
            "user": {"id": user.id, "username": user.username, "role": user.role},
        })
        json_resp.set_cookie(
            key="access_token",
            value=token,
            max_age=max_age,
            httponly=True,
            samesite="lax",
            path="/"
        )
        return json_resp
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.error(f"Login error: {exc}")
        raise HTTPException(status_code=500, detail="Authentication failed.")


@app.post("/api/auth/register")
def register(req: RegisterRequest) -> JSONResponse:
    auth_manager = get_auth_manager()
    try:
        provider = auth_manager.get_provider("postgres")
        if not isinstance(provider, PostgresAuthProvider):
            raise HTTPException(status_code=400, detail="Registration not supported on current provider.")

        user = provider.register_user(req.username, req.password)
        token = provider.create_token(user)

        max_age = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "72")) * 3600
        json_resp = JSONResponse({
            "status": "success",
            "message": f"Account '{user.username}' created successfully!",
            "token": token,
            "user": {"id": user.id, "username": user.username, "role": user.role},
        })
        json_resp.set_cookie(
            key="access_token",
            value=token,
            max_age=max_age,
            httponly=True,
            samesite="lax",
            path="/"
        )
        return json_resp
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Registration error: {exc}")
        raise HTTPException(status_code=500, detail="Registration failed.")


@app.post("/api/auth/logout")
def logout() -> JSONResponse:
    json_resp = JSONResponse({"status": "success", "message": "Logged out successfully."})
    json_resp.delete_cookie(key="access_token", path="/")
    return json_resp


@app.get("/api/auth/me")
def me(user: Optional[User] = Depends(get_optional_user)) -> JSONResponse:
    if not user:
        return JSONResponse({"authenticated": False, "user": None, "db": get_active_db_type()})
    return JSONResponse({
        "authenticated": True,
        "user": {"id": user.id, "username": user.username, "role": user.role},
        "db": get_active_db_type(),
    })


# ---------------------------------------------------------
# Core Application Endpoints
# ---------------------------------------------------------

@app.get('/', response_class=HTMLResponse)
def get_ui() -> HTMLResponse:
    html_path = STATIC_DIR / 'index.html'
    if not html_path.exists():
        raise HTTPException(status_code=404, detail='UI not found')
    return HTMLResponse(content=html_path.read_text(encoding='utf-8'))


@app.get('/api/status')
def status(user: Optional[User] = Depends(get_optional_user)) -> JSONResponse:
    ensure_directories()
    clip_files = sorted([p.name for p in CLIPS_DIR.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS])
    return JSONResponse({
        'clips': clip_files,
        'output_exists': OUTPUT_VIDEO.exists(),
        'download_url': '/api/download/output' if OUTPUT_VIDEO.exists() else None,
        'authenticated': user is not None,
        'user': {"username": user.username} if user else None,
        'database': get_active_db_type(),
        'model': os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    })


@app.post('/api/upload')
def upload_clips(
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user)
) -> JSONResponse:
    ensure_directories()
    uploaded = []
    for upload_file in files:
        if upload_file.filename == '':
            continue
        destination = CLIPS_DIR / upload_file.filename
        with destination.open('wb') as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        uploaded.append(upload_file.filename)
        logger.info(f'User [{user.username}] uploaded clip: {upload_file.filename}')
    return JSONResponse({'uploaded': uploaded, 'message': f'Uploaded {len(uploaded)} file(s).'})


@app.post('/api/upload/chunk')
def upload_clip_chunk(
    file: UploadFile = File(...),
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    ensure_directories()
    clean_name = Path(filename).name
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    temp_dir = DATA_DIR / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    user_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', user.id)
    part_file = temp_dir / f"{user_prefix}_{clean_name}.part_{chunk_index}"

    # If first chunk, clean up any previous stale parts for this file
    if chunk_index == 0:
        for old_part in temp_dir.glob(f"{user_prefix}_{clean_name}.part_*"):
            try:
                old_part.unlink(missing_ok=True)
            except Exception:
                pass

    with part_file.open('wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    # When final chunk is received, assemble into destination
    if chunk_index == total_chunks - 1:
        destination = CLIPS_DIR / clean_name
        with destination.open('wb') as out_buffer:
            for i in range(total_chunks):
                p = temp_dir / f"{user_prefix}_{clean_name}.part_{i}"
                if not p.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Upload interrupted: missing part {i} of {total_chunks} for {clean_name}."
                    )
                with p.open('rb') as in_part:
                    shutil.copyfileobj(in_part, out_buffer)
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

        logger.info(f"User [{user.username}] completed chunked upload: {clean_name} ({total_chunks} chunk(s))")
        return JSONResponse({
            "status": "complete",
            "filename": clean_name,
            "message": f"Successfully uploaded {clean_name}.",
        })

    return JSONResponse({
        "status": "chunk_received",
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
    })


@app.post('/api/render')
def render_prompt(
    prompt: str = Form(...),
    use_resolve: bool = Form(False),
    user: User = Depends(get_current_user)
) -> JSONResponse:
    ensure_directories()
    try:
        clips = scan_clips(CLIPS_DIR)
        if not clips:
            raise HTTPException(status_code=400, detail='No clips uploaded. Please upload video clips before rendering.')

        manifest = ingest_clips(CLIPS_DIR)
        if not manifest:
            raise HTTPException(status_code=500, detail='Failed to ingest clips.')
        save_manifest(manifest, DATA_DIR)

        transcribe_clips(clips, TRANSCRIPTS_DIR, model_name='small')

        vector_store, _ = build_index(TRANSCRIPTS_DIR, DATA_DIR, embedding_model='all-MiniLM-L6-v2', use_multimodal=False)
        embedding_provider = EmbeddingProvider(model_name='all-MiniLM-L6-v2')
        retrieved_segments = retrieve_segments(prompt, vector_store, embedding_provider, top_k=5)
        if not retrieved_segments:
            raise HTTPException(status_code=500, detail='No relevant segments found for the prompt.')

        gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        logger.info(f"User [{user.username}] generating plan with Gemini ({gemini_model})")
        edit_plan = plan_edit(prompt, retrieved_segments, model_name=gemini_model)
        
        plan_path = DATA_DIR / 'edit_plan.json'
        plan_json_str = edit_plan.model_dump_json(indent=2)
        plan_path.write_text(plan_json_str, encoding='utf-8')

        render_plan(edit_plan, CLIPS_DIR, OUTPUT_VIDEO, manifest_path=DATA_DIR / 'clips_manifest.json', use_resolve=use_resolve)

        # Log render job to database
        session = get_session()
        try:
            job = RenderJobRecord(
                id=str(uuid.uuid4()),
                user_id=user.id,
                prompt=prompt,
                status="completed",
                edit_plan=json.loads(plan_json_str),
                output_path=str(OUTPUT_VIDEO),
            )
            session.add(job)
            session.commit()
            logger.info(f"Logged render job {job.id} for user {user.username}")
        except Exception as exc:
            session.rollback()
            logger.warning(f"Failed to record render job to database: {exc}")
        finally:
            session.close()

        return JSONResponse({
            'status': 'completed',
            'output_url': '/api/download/output',
            'plan': json.loads(plan_path.read_text(encoding='utf-8')),
        })
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Render pipeline failed')
        raise HTTPException(status_code=500, detail=str(exc))


@app.get('/api/download/output')
def download_output(user: User = Depends(get_current_user)) -> FileResponse:
    ensure_directories()
    if not OUTPUT_VIDEO.exists():
        raise HTTPException(status_code=404, detail='Final output not found. Please generate a video first.')
    logger.info(f"User [{user.username}] downloading final output video.")
    return FileResponse(path=OUTPUT_VIDEO, filename=OUTPUT_VIDEO.name, media_type='video/mp4')
