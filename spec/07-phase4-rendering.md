# Implementation Spec: Phase 4 - FFmpeg Execution & Rendering

## Objective
Implement the execution engine to render video based on the edit plan from Phase 3, using FFmpeg for trimming and concatenation.

## Scope

### Execution Engine
- **Input:** EditPlan JSON file with timeline and style config
- **Process:**
  1. Validate edit plan against actual video files
  2. For each clip segment in timeline:
     - Locate the source video file
     - Trim the segment using FFmpeg (start/end times)
     - Write to temporary file
  3. Concatenate all trimmed segments in order
  4. Apply aspect ratio scaling if needed (e.g., 9:16)
  5. Write final output video
- **Output:** Final rendered MP4 file
- **Location:** `backend/services/executor.py` and `backend/services/ffmpeg_runner.py`

### FFmpeg Runner
- **Trim Operation:**
  ```bash
  ffmpeg -ss START -to END -i input.mp4 -c copy output.mp4
  ```
- **Concatenation:**
  - Create concat list file with paths to trimmed segments
  - Use FFmpeg concat demuxer
  ```bash
  ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
  ```
- **Aspect Ratio Scaling (optional):**
  - For 9:16: scale to 1080x1920 with padding
  - For 16:9: default, no scaling
  ```bash
  ffmpeg -i input.mp4 -vf scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920 -preset fast output.mp4
  ```

### Rendering Pipeline
- **Temp Directory:** `data/render_temp/` for intermediate files
- **Cleanup:** Remove temp files after successful render or on error
- **Error Recovery:** If rendering fails at any step, rollback and report error
- **Progress Tracking:** Log progress for each segment (e.g., "Trimmed 3/10 segments")

### Validation Engine
- **Pre-render checks:**
  1. Verify edit plan JSON is valid
  2. Check that all referenced clips exist
  3. Ensure timestamps are within clip bounds (with tolerance)
  4. Verify FFmpeg is installed and accessible
- **Post-render checks:**
  1. Verify output file exists and has size > 0
  2. Verify output duration matches expected duration
  3. Optional: frame sample validation

### CLI Commands (Phase 4)
- `python backend/main.py render` — renders using default paths
- `python backend/main.py render --plan data/custom_plan.json --output custom_output.mp4`

### Data Files
- Input: `data/edit_plan.json` (from Phase 3)
- Output: `data/outputs/final.mp4` (default) or custom path
- Temp: `data/render_temp/` (cleaned up after render)

## Dependencies
- ffmpeg (system binary, v4.0+)
- ffmpeg-python (Python wrapper)
- pathlib (file operations)

## Success Criteria
1. FFmpeg trims segments with accurate start/end times
2. Segments concatenate in correct order without re-encoding
3. Aspect ratio scaling works for 9:16 and maintains quality
4. Temp files are cleaned up after successful render
5. Output video plays correctly in standard players
6. Rendering handles missing clips gracefully with clear error messages
7. Progress is logged for transparency
8. Concurrent renders can run with isolated temp directories

## Notes
- Use `-c copy` codec to avoid re-encoding for speed
- Use `-preset fast` for scaling to balance quality and speed
- Consider adding fade transitions in future iterations
- Could add subtitle overlay support in future
- Output file format is MP4 by default but can be made configurable
