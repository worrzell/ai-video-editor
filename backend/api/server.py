import json
import logging
import shutil
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.services.ingestion import ingest_clips, save_manifest, scan_clips
from backend.services.transcription import transcribe_clips
from backend.services.indexing import build_index
from backend.services.embedding import EmbeddingProvider
from backend.services.retrieval import retrieve_segments
from backend.services.planner import plan_edit
from backend.services.executor import render_plan
from backend.models.edit_plan import EditPlan

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

app = FastAPI(title='AI Video Editor')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


def ensure_directories() -> None:
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get('/', response_class=HTMLResponse)
def get_ui() -> HTMLResponse:
    html_path = STATIC_DIR / 'index.html'
    if not html_path.exists():
        raise HTTPException(status_code=404, detail='UI not found')
    return HTMLResponse(content=html_path.read_text(encoding='utf-8'))


@app.get('/api/status')
def status() -> JSONResponse:
    ensure_directories()
    clip_files = sorted([p.name for p in CLIPS_DIR.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS])
    return JSONResponse({
        'clips': clip_files,
        'output_exists': OUTPUT_VIDEO.exists(),
        'download_url': '/api/download/output' if OUTPUT_VIDEO.exists() else None,
    })


@app.post('/api/upload')
def upload_clips(files: List[UploadFile] = File(...)) -> JSONResponse:
    ensure_directories()
    uploaded = []
    for upload_file in files:
        if upload_file.filename == '':
            continue
        destination = CLIPS_DIR / upload_file.filename
        with destination.open('wb') as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        uploaded.append(upload_file.filename)
        logger.info(f'Uploaded clip: {upload_file.filename}')
    return JSONResponse({'uploaded': uploaded, 'message': f'Uploaded {len(uploaded)} file(s).'})


@app.post('/api/render')
def render_prompt(prompt: str = Form(...), use_resolve: bool = Form(False)) -> JSONResponse:
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

        edit_plan = plan_edit(prompt, retrieved_segments, model_name='llama3')
        plan_path = DATA_DIR / 'edit_plan.json'
        plan_path.write_text(edit_plan.model_dump_json(indent=2), encoding='utf-8')

        render_plan(edit_plan, CLIPS_DIR, OUTPUT_VIDEO, manifest_path=DATA_DIR / 'clips_manifest.json', use_resolve=use_resolve)

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
def download_output() -> FileResponse:
    ensure_directories()
    if not OUTPUT_VIDEO.exists():
        raise HTTPException(status_code=404, detail='Final output not found. Please generate a video first.')
    return FileResponse(path=OUTPUT_VIDEO, filename=OUTPUT_VIDEO.name, media_type='video/mp4')
