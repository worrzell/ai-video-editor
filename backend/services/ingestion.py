from pathlib import Path
import json
import subprocess
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv'}


def scan_clips(clips_dir: Path) -> List[Path]:
    """Scan directory for video files."""
    clips_dir = Path(clips_dir)
    if not clips_dir.exists():
        raise FileNotFoundError(f'Clips directory not found: {clips_dir}')
    if not clips_dir.is_dir():
        raise NotADirectoryError(f'Not a directory: {clips_dir}')
    
    clips = sorted([p for p in clips_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS])
    logger.info(f'Found {len(clips)} video clips in {clips_dir}')
    return clips


def extract_metadata(input_path: Path) -> Dict:
    """Extract metadata from a video file using ffprobe."""
    command = [
        'ffprobe',
        '-v', 'error',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(input_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f'ffprobe failed: {result.stderr.strip()}')
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'ffprobe timeout for {input_path.name}')
    except json.JSONDecodeError as e:
        raise RuntimeError(f'ffprobe returned invalid JSON: {e}')
    
    format_info = data.get('format', {})
    video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    video_stream = video_streams[0] if video_streams else {}
    
    clip_id = input_path.stem
    metadata = {
        'clip_id': clip_id,
        'path': str(input_path),
        'filename': input_path.name,
        'duration': float(format_info.get('duration', 0.0)),
        'fps': float(video_stream.get('r_frame_rate', '0/1').split('/')[0]) if video_stream and 'r_frame_rate' in video_stream else None,
        'width': int(video_stream.get('width', 0)) if video_stream else None,
        'height': int(video_stream.get('height', 0)) if video_stream else None,
    }
    return metadata


def ingest_clips(clips_dir: Path) -> List[Dict]:
    """Ingest all clips and return metadata list."""
    clips = scan_clips(clips_dir)
    metadata_list = []
    failed = []
    
    for clip_path in clips:
        try:
            metadata = extract_metadata(clip_path)
            metadata_list.append(metadata)
            logger.info(f'Ingested {clip_path.name} ({metadata["duration"]:.1f}s)')
        except Exception as e:
            logger.error(f'Failed to ingest {clip_path.name}: {e}')
            failed.append((clip_path.name, str(e)))
    
    if failed:
        logger.warning(f'{len(failed)} clip(s) failed to ingest')
    
    return metadata_list


def save_manifest(metadata_list: List[Dict], output_dir: Path) -> Path:
    """Save metadata manifest to JSON file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / 'clips_manifest.json'
    manifest_data = {
        'total_clips': len(metadata_list),
        'clips': metadata_list,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info(f'Saved manifest to {manifest_path}')
    return manifest_path
