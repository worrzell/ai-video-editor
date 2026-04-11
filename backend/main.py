#!/usr/bin/env python3
"""
AI Video Editing Tool - Main Entry Point
"""

import json
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import typer

from backend.services.ingestion import ingest_clips, save_manifest, scan_clips
from backend.services.transcription import transcribe_clips
from backend.services.indexing import build_index, load_index
from backend.services.retrieval import retrieve_segments, retrieve_segments_from_all_clips
from backend.services.embedding import EmbeddingProvider
from backend.services.planner import plan_edit
from backend.services.executor import render_plan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer()

DATA_DIR = Path('data')
CLIPS_DIR = DATA_DIR / 'clips'
TRANSCRIPTS_DIR = DATA_DIR / 'transcripts'
MANIFEST_FILE = DATA_DIR / 'clips_manifest.json'

@app.command()
def ingest(clips_dir: Path = typer.Argument(CLIPS_DIR, help='Directory containing video clips')):
    """Ingest video clips and generate metadata manifest."""
    typer.echo(f'[*] Ingesting clips from {clips_dir}')
    try:
        metadata_list = ingest_clips(clips_dir)
        if not metadata_list:
            typer.echo('No clips found.')
            return
        
        save_manifest(metadata_list, DATA_DIR)
        for metadata in metadata_list:
            typer.echo(f"  ✓ {metadata['filename']} ({metadata['duration']:.1f}s)")
        typer.echo(f'[✓] Ingested {len(metadata_list)} clip(s).')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        raise typer.Exit(1)

@app.command()
def process(clips_dir: Path = typer.Option(CLIPS_DIR, help='Clips directory'), transcripts_dir: Path = typer.Option(TRANSCRIPTS_DIR, help='Output transcripts directory'), whisper_model: str = typer.Option('small', help='Whisper model size'), language: str = typer.Option(None, help='Language code (auto-detect if not specified)'), include_visual: bool = typer.Option(False, help='Extract visual features from video frames using CLIP')):
    """Process clips: transcription, segment extraction, and optional visual feature extraction."""
    typer.echo('[*] Processing clips...')
    try:
        clips = scan_clips(clips_dir)
        if not clips:
            typer.echo('No clips found to process.')
            return
        
        transcripts = transcribe_clips(clips, transcripts_dir, model_name=whisper_model, language=language, include_visual=include_visual)
        for transcript in transcripts:
            num_segments = len(transcript['segments'])
            lang = transcript['language']
            has_visual = any('visual_description' in seg for seg in transcript['segments']) if include_visual else False
            visual_status = " (with visual)" if has_visual else ""
            typer.echo(f"  ✓ {transcript['filename']} ({num_segments} segments, lang: {lang}){visual_status}")
        typer.echo(f'[✓] Processed {len(transcripts)} clip(s).')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        logger.exception('Processing failed')
        raise typer.Exit(1)

@app.command()
def generate(prompt: str = typer.Argument(..., help='Natural language prompt for editing'), transcripts_dir: Path = typer.Option(TRANSCRIPTS_DIR, help='Transcripts directory')):
    """Generate edit plan from prompt (requires Phase 2+)."""
    typer.echo(f'[*] Generating plan for: {prompt}')
    typer.echo('[!] Phase 2 (embeddings & retrieval) not yet implemented.')
    raise typer.Exit(1)

@app.command()
def plan(prompt: str = typer.Argument(..., help='Edit request'), output_dir: Path = typer.Option(DATA_DIR, help='Output directory with index'), top_k: int = typer.Option(5, help='Top-k segments for LLM'), use_all_clips: bool = typer.Option(False, help='Sample segments from all clips instead of semantic retrieval'), segments_per_clip: int = typer.Option(3, help='Segments per clip when using all clips'), embedding_model: str = typer.Option('all-MiniLM-L6-v2', help='Embedding model'), ollama_model: str = typer.Option('llama3', help='Ollama model name')):
    """Generate edit plan using LLM planning (Phase 3)."""
    typer.echo(f'[*] Planning edit for: "{prompt}"')
    try:
        # Load index and search
        vector_store = load_index(output_dir)
        if use_all_clips:
            retrieved = retrieve_segments_from_all_clips(vector_store, segments_per_clip=segments_per_clip)
        else:
            embedding_provider = EmbeddingProvider(model_name=embedding_model)
            retrieved = retrieve_segments(prompt, vector_store, embedding_provider, top_k=top_k)
        
        if not retrieved:
            typer.echo('[!] No segments retrieved. Cannot generate plan.', err=True)
            raise typer.Exit(1)
        
        # Generate plan with LLM
        typer.echo(f'[*] Calling LLM to generate plan...')
        edit_plan = plan_edit(prompt, retrieved, model_name=ollama_model)
        
        # Save plan
        plan_path = output_dir / 'edit_plan.json'
        plan_path.write_text(edit_plan.model_dump_json(indent=2), encoding='utf-8')
        
        typer.echo(f'[✓] Plan generated with {len(edit_plan.timeline)} segments:')
        for i, segment in enumerate(edit_plan.timeline, 1):
            typer.echo(f'  {i}. [{segment.clip_id}] {segment.start:.1f}s-{segment.end:.1f}s')
        typer.echo(f'  Style: pace={edit_plan.style.pace}, captions={edit_plan.style.captions}, aspect_ratio={edit_plan.style.aspect_ratio}')
        typer.echo(f'[✓] Plan saved to {plan_path}')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        logger.exception('Plan generation failed')
        raise typer.Exit(1)

@app.command()
def index(transcripts_dir: Path = typer.Option(TRANSCRIPTS_DIR, help='Transcripts directory'), output_dir: Path = typer.Option(DATA_DIR, help='Output directory for index'), embedding_model: str = typer.Option('all-MiniLM-L6-v2', help='Embedding model name'), use_multimodal: bool = typer.Option(True, help='Use multimodal embeddings if visual features are available')):
    """Build FAISS index from transcripts with optional multimodal embeddings."""
    typer.echo('[*] Building FAISS index from transcripts...')
    try:
        vector_store, segments = build_index(transcripts_dir, output_dir, embedding_model=embedding_model, use_multimodal=use_multimodal)
        
        # Check if visual features were used
        has_visual = any('visual_embedding' in seg for seg in segments)
        mode_str = "multimodal (text + visual)" if (has_visual and use_multimodal) else "text-only"
        
        typer.echo(f'[✓] Index built with {len(segments)} segments.')
        typer.echo(f'  - Embedding model: {embedding_model}')
        typer.echo(f'  - Mode: {mode_str}')
        typer.echo(f'  - Index file: {output_dir / "embeddings.index"}')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        logger.exception('Indexing failed')
        raise typer.Exit(1)

@app.command()
def search(prompt: str = typer.Argument(..., help='Search query'), output_dir: Path = typer.Option(DATA_DIR, help='Output directory with index'), top_k: int = typer.Option(5, help='Number of results to return'), embedding_model: str = typer.Option('all-MiniLM-L6-v2', help='Embedding model name')):
    """Search the FAISS index for relevant segments."""
    typer.echo(f'[*] Searching for: "{prompt}"')
    try:
        vector_store = load_index(output_dir)
        embedding_provider = EmbeddingProvider(model_name=embedding_model)
        results = retrieve_segments(prompt, vector_store, embedding_provider, top_k=top_k)
        
        typer.echo(f'[✓] Found {len(results)} relevant segments:')
        for i, result in enumerate(results, 1):
            start_time = result['start']
            end_time = result['end']
            clip_id = result['clip_id']
            text_preview = result['text'][:60].replace('\n', ' ')
            score = result['score']
            typer.echo(f'  {i}. [{clip_id}] {start_time:.1f}s-{end_time:.1f}s (score: {score:.4f})')
            typer.echo(f'     "{text_preview}..."')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        raise typer.Exit(1)

@app.command()
def render(edit_plan_path: Path = typer.Option(DATA_DIR / 'edit_plan.json', help='Edit plan JSON file'), clips_dir: Path = typer.Option(CLIPS_DIR, help='Clips directory'), output_path: Path = typer.Option(DATA_DIR / 'outputs' / 'final.mp4', help='Output video path')):
    """Render the final video (Phase 4)."""
    typer.echo(f'[*] Rendering video from plan: {edit_plan_path}')
    try:
        # Load edit plan
        if not edit_plan_path.exists():
            typer.echo(f'[!] Edit plan not found: {edit_plan_path}', err=True)
            raise typer.Exit(1)
        
        import json
        from backend.models.edit_plan import EditPlan
        plan_data = json.loads(edit_plan_path.read_text(encoding='utf-8'))
        edit_plan = EditPlan(**plan_data)
        
        # Render
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = DATA_DIR / 'clips_manifest.json'
        output = render_plan(edit_plan, clips_dir, output_path, manifest_path=manifest_path if manifest_path.exists() else None)
        
        typer.echo(f'[✓] Video rendered successfully: {output}')
        typer.echo(f'  - Segments: {len(edit_plan.timeline)}')
        typer.echo(f'  - Aspect ratio: {edit_plan.style.aspect_ratio}')
        typer.echo(f'  - Captions: {edit_plan.style.captions}')
    except Exception as e:
        typer.echo(f'[!] Error: {e}', err=True)
        logger.exception('Render failed')
        raise typer.Exit(1)

if __name__ == '__main__':
    app()
