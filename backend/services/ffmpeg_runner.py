import logging
from pathlib import Path
import subprocess
from typing import List

logger = logging.getLogger(__name__)


def trim_clip(input_path: Path, output_path: Path, start: float, end: float, timeout: int = 300):
    """Trim a video clip to specified time range using FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    command = [
        'ffmpeg',
        '-y',
        '-ss', f'{start:.2f}',
        '-to', f'{end:.2f}',
        '-i', str(input_path),
        '-c', 'copy',
        '-loglevel', 'error',
        str(output_path),
    ]
    
    try:
        logger.info(f'Trimming {input_path.name} ({start:.2f}s-{end:.2f}s) -> {output_path.name}')
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f'ffmpeg trim failed: {result.stderr}')
        logger.info(f'Trimmed segment saved: {output_path}')
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'ffmpeg trim timeout for {input_path.name}')


def concat_clips(segment_paths: List[Path], output_path: Path, aspect_ratio: str = '16:9', timeout: int = 600):
    """Concatenate video clips using FFmpeg concat demuxer."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create concat file
    concat_file = output_path.parent / 'concat_list.txt'
    concat_lines = [f"file '{p.resolve()}'" for p in segment_paths]
    concat_file.write_text('\n'.join(concat_lines), encoding='utf-8')
    logger.info(f'Created concat file: {concat_file}')
    
    # Build FFmpeg command
    command = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-loglevel', 'error',
    ]
    
    # Add aspect ratio scaling if needed
    if aspect_ratio == '9:16':
        command.extend([
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
            '-preset', 'fast',
        ])
    else:
        command.extend(['-c', 'copy'])
    
    command.append(str(output_path))
    
    try:
        logger.info(f'Concatenating {len(segment_paths)} segments to {output_path.name} (aspect_ratio={aspect_ratio})')
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f'ffmpeg concat failed: {result.stderr}')
        logger.info(f'Concatenation complete: {output_path}')
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'ffmpeg concat timeout ({timeout}s)')
    finally:
        # Cleanup concat file
        if concat_file.exists():
            concat_file.unlink()
            logger.debug(f'Cleaned up concat file: {concat_file}')


def verify_output(output_path: Path) -> bool:
    """Verify the output video file."""
    if not output_path.exists():
        raise FileNotFoundError(f'Output file not created: {output_path}')
    
    file_size = output_path.stat().st_size
    if file_size == 0:
        raise RuntimeError(f'Output file is empty: {output_path}')
    
    logger.info(f'Output file verified: {output_path} ({file_size / 1024 / 1024:.1f} MB)')
    return True

