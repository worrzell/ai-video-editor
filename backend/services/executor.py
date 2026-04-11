import logging
import shutil
from pathlib import Path
from typing import Dict, List

from backend.models.edit_plan import EditPlan
from backend.services.ffmpeg_runner import trim_clip, concat_clips, verify_output

logger = logging.getLogger(__name__)


def validate_plan_against_clips(edit_plan: EditPlan, clips_dir: Path, manifest_path: Path = None) -> None:
    """Validate that all segments in the plan can be sourced from available clips."""
    logger.info('Validating edit plan against available clips...')
    
    # Load manifest if available
    manifest = {}
    if manifest_path and manifest_path.exists():
        import json
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest = {clip['clip_id']: clip for clip in data.get('clips', [])}
    
    # Check each segment
    for i, segment in enumerate(edit_plan.timeline, 1):
        clip_id = segment.clip_id
        
        # Find clip file
        clip_files = list(clips_dir.glob(f'{clip_id}.*'))
        if not clip_files:
            raise FileNotFoundError(f'Clip not found for clip_id: {clip_id}')
        
        clip_path = clip_files[0]
        
        # Validate timestamps
        if manifest and clip_id in manifest:
            clip_duration = manifest[clip_id]['duration']
            if segment.end > clip_duration:
                logger.warning(f'Segment end time ({segment.end}s) exceeds clip duration ({clip_duration}s); clipping.')
        
        logger.info(f'  [{i}] {clip_id}: {segment.start:.2f}s-{segment.end:.2f}s ✓')


def render_plan(edit_plan: EditPlan, clips_dir: Path, output_path: Path, manifest_path: Path = None) -> Path:
    """Render a video from an edit plan."""
    clips_dir = Path(clips_dir)
    output_path = Path(output_path)
    temp_dir = output_path.parent / 'render_temp'
    
    try:
        logger.info(f'Starting render: {len(edit_plan.timeline)} segments')
        
        # Validate plan
        validate_plan_against_clips(edit_plan, clips_dir, manifest_path)
        
        # Create temp directory
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f'Using temp directory: {temp_dir}')
        
        # Trim segments
        segment_files = []
        for index, segment in enumerate(edit_plan.timeline):
            clip_files = list(clips_dir.glob(f'{segment.clip_id}.*'))
            if not clip_files:
                raise FileNotFoundError(f'Clip not found for {segment.clip_id}')
            
            clip_path = clip_files[0]
            output_segment = temp_dir / f'segment_{index:03d}.mp4'
            
            trim_clip(clip_path, output_segment, segment.start, segment.end)
            segment_files.append(output_segment)
            logger.info(f'Trimmed segment {index + 1}/{len(edit_plan.timeline)}')
        
        # Concatenate segments
        output_path.parent.mkdir(parents=True, exist_ok=True)
        concat_clips(segment_files, output_path, aspect_ratio=edit_plan.style.aspect_ratio)
        
        # Verify output
        verify_output(output_path)
        logger.info(f'Render complete: {output_path}')
        
        return output_path
    
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f'Cleaned up temp directory: {temp_dir}')
            except Exception as e:
                logger.warning(f'Failed to clean up temp directory: {e}')
