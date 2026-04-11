# Implementation Spec: Phase 1 - Ingestion & Transcription

## Objective
Implement the ingestion and transcription pipeline to extract metadata and generate transcript files from raw video clips.

## Scope

### Ingestion Service
- **Input:** Directory containing raw video clips (*.mp4, *.mov, *.mkv, *.avi)
- **Process:**
  1. Scan the directory for video files
  2. Extract metadata using FFprobe (duration, fps, resolution, codec)
  3. Store metadata in a JSON manifest
- **Output:** Metadata file per clip in `data/clips_manifest.json` or similar
- **Location:** `backend/services/ingestion.py`

### Transcription Service
- **Input:** List of video files from ingestion
- **Process:**
  1. Extract audio from each clip
  2. Run Whisper locally (default model: small)
  3. Generate segment-level transcripts with start/end times
- **Output:** JSON file per clip in `data/transcripts/` directory
- **Format:** 
  ```json
  {
    "clip_id": "clip_001",
    "duration": 120.5,
    "language": "en",
    "segments": [
      {"start": 0.0, "end": 3.5, "text": "Hello world"},
      {"start": 3.5, "end": 8.2, "text": "This is a test"}
    ]
  }
  ```
- **Location:** `backend/services/transcription.py`

### CLI Commands (Phase 1)
- `python backend/main.py ingest ./data/clips/` — scans directory and extracts metadata
- `python backend/main.py process` — transcribes all clips in data/clips/

### Data Files
- `data/clips/` — input raw video clips (user-provided)
- `data/clips_manifest.json` — metadata index for all clips
- `data/transcripts/*.json` — individual transcript files

## Dependencies
- ffmpeg (system binary)
- ffmpeg-python (Python wrapper)
- openai-whisper (transcription)
- pydantic (data validation)

## Success Criteria
1. `ingest` command scans a directory of clips and generates metadata without errors
2. `process` command transcribes all clips and generates transcript JSON files
3. Transcript files contain accurate start/end times and segment text
4. All errors (missing clips, ffmpeg failures) are logged clearly
5. Metadata and transcripts are persisted to disk

## Notes
- Whisper model size can be passed as a CLI option (--whisper-model default: small)
- FFmpeg errors should be captured and reported to the user
- Transaction atomicity: if one clip fails, log it but continue processing others
