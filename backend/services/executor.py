import logging
import shutil
from pathlib import Path
from typing import Dict, List
import subprocess

from backend.models.edit_plan import EditPlan
from backend.services.ffmpeg_runner import trim_clip, concat_clips, verify_output

def render_with_resolve(segment_files: List[Path], output_path: Path, edit_plan: EditPlan) -> Path:
    """Render using DaVinci Resolve for advanced post-processing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a simple Resolve project file (DRP format)
    project_file = output_path.parent / 'temp_project.drp'
    create_resolve_project(segment_files, project_file, edit_plan)

    try:
        # Use Resolve command-line rendering (if available)
        # Note: This requires DaVinci Resolve Studio with command-line tools
        cmd = [
            'resolve',  # or full path to resolve executable
            '-p', str(project_file),
            '-o', str(output_path),
            '--format', 'mp4',
            '--quality', 'high'
        ]

        logger.info(f'Rendering with DaVinci Resolve: {len(segment_files)} segments')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout

        if result.returncode != 0:
            logger.warning(f'Resolve rendering failed: {result.stderr}')
            # Fallback to FFmpeg
            logger.info('Falling back to FFmpeg rendering')
            concat_clips(segment_files, output_path, aspect_ratio=edit_plan.style.aspect_ratio)
        else:
            logger.info(f'Resolve render complete: {output_path}')

        verify_output(output_path)
        return output_path

    finally:
        # Cleanup project file
        if project_file.exists():
            project_file.unlink()


def create_resolve_project(segment_files: List[Path], project_file: Path, edit_plan: EditPlan):
    """Create a basic DaVinci Resolve project file."""
    # This is a simplified DRP (DaVinci Resolve Project) structure
    # In practice, you'd need to create proper XML/JSON structure
    project_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ResolveProject>
    <Timeline>
        <Tracks>
            <VideoTrack>
"""

    current_time = 0
    for i, segment_file in enumerate(segment_files):
        duration = 5.0  # Placeholder - you'd need to get actual duration
        project_content += f"""
                <Clip index="{i}" start="{current_time}" duration="{duration}">
                    <MediaPath>{segment_file.resolve()}</MediaPath>
                </Clip>"""
        current_time += duration

    project_content += """
            </VideoTrack>
        </Tracks>
    </Timeline>
</ResolveProject>"""

    project_file.write_text(project_content, encoding='utf-8')
    logger.info(f'Created Resolve project: {project_file}')
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


def render_plan(edit_plan: EditPlan, clips_dir: Path, output_path: Path, manifest_path: Path = None, use_resolve: bool = False) -> Path:
    """Render a video from an edit plan."""
    clips_dir = Path(clips_dir)
    output_path = Path(output_path)
    temp_dir = output_path.parent / 'render_temp'

    try:
        logger.info(f'Starting render: {len(edit_plan.timeline)} segments (resolve={use_resolve})')

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

        if use_resolve:
            # Use DaVinci Resolve for final rendering
            return render_with_resolve(segment_files, output_path, edit_plan)
        else:
            # Use FFmpeg for concatenation
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
