# AI Video Editing Tool (Local-First) — Technical Spec

## 1. Goal

Build a local-first AI-powered video editing tool that:

* Accepts multiple raw video clips
* Accepts a natural language prompt
* Automatically generates a rough-cut edited video
* Runs fully offline using local models and tools

---

## 2. Core Concept

Pipeline:

User Input (Prompt + Clips)
→ Media Understanding
→ Context Indexing
→ Retrieval
→ LLM Planning (structured JSON)
→ Execution Engine (FFmpeg / Editor)
→ Output Video

---

## 3. System Architecture

### 3.1 Modules

1. Ingestion Service
2. Media Processing Pipeline
3. Context Store (Vector DB)
4. LLM Planner (Local)
5. Editing DSL (JSON schema)
6. Execution Engine
7. API Layer
8. Frontend UI (optional initially CLI)

---

## 4. Tech Stack

### Backend

* Python (preferred) OR Node.js
* FastAPI (if Python)

### LLM (Local)

* Ollama
* Models:

  * llama3 / mistral / mixtral

### Transcription

* Whisper (local)

### Embeddings

* sentence-transformers OR Ollama embeddings

### Vector DB

* FAISS (local)

### Video Processing

* FFmpeg (mandatory)

### Optional Editor Integration

* DaVinci Resolve (Python API)
* Kdenlive (optional)

---

## 5. Folder Structure

project-root/
│
├── backend/
│   ├── main.py
│   ├── api/
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── transcription.py
│   │   ├── embedding.py
│   │   ├── retrieval.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   └── ffmpeg_runner.py
│   │
│   ├── models/
│   │   └── edit_plan.py
│   │
│   ├── db/
│   │   └── vector_store.py
│   │
│   └── utils/
│
├── data/
│   ├── clips/
│   ├── transcripts/
│   └── outputs/
│
├── scripts/
├── frontend/ (optional)
└── README.md

---

## 6. Data Flow

### Step 1: Ingestion

* Input: video files
* Extract:

  * audio
  * metadata (duration, fps)

---

### Step 2: Transcription

* Use Whisper locally
* Output:
  {
  "clip_id": "...",
  "segments": [
  {"start": 0.0, "end": 3.2, "text": "..."}
  ]
  }

---

### Step 3: Embeddings + Indexing

* Convert transcript segments → embeddings
* Store in FAISS:
  {
  embedding,
  clip_id,
  start,
  end,
  text
  }

---

### Step 4: Retrieval

* Input: user prompt
* Convert prompt → embedding
* Retrieve top-k relevant segments

---

### Step 5: LLM Planning (CRITICAL)

Use Ollama LLM.

INPUT:

* User prompt
* Retrieved segments

OUTPUT:
STRICT JSON ONLY (no prose)

Example:

{
"timeline": [
{
"clip_id": "clip_01",
"start": 12.3,
"end": 25.0,
"reason": "important highlight"
}
],
"style": {
"pace": "fast",
"captions": true,
"aspect_ratio": "9:16"
}
}

Constraints:

* MUST only use provided clip_ids
* MUST include timestamps
* NO hallucination

---

## 7. Editing DSL (Schema)

Create Pydantic model:

EditPlan:

* timeline: list[ClipSegment]
* style: StyleConfig

ClipSegment:

* clip_id: str
* start: float
* end: float

StyleConfig:

* pace: str
* captions: bool
* aspect_ratio: str

---

## 8. Execution Engine

### v1 (MANDATORY)

Use FFmpeg only.

Steps:

1. Trim clips:
   ffmpeg -ss START -to END -i input.mp4 -c copy out.mp4

2. Concatenate clips:
   ffmpeg concat

3. Optional:

   * scale to 9:16
   * basic subtitles

---

### v2 (OPTIONAL)

* Add transitions
* Add captions overlay
* Add zoom/pan

---

## 9. API Design

### POST /ingest

* Upload clips

### POST /process

* Runs transcription + embeddings

### POST /generate

* Input: prompt
* Output: edit plan

### POST /render

* Input: edit plan
* Output: final video

---

## 10. CLI (for MVP)

Commands:

python main.py ingest ./clips/
python main.py process
python main.py generate "create a cinematic vlog"
python main.py render

---

## 11. Constraints

* Fully offline (no cloud APIs)
* Deterministic outputs where possible
* LLM must output valid JSON (use structured prompting)

---

## 12. Future Enhancements

* DaVinci Resolve integration
* Timeline preview UI
* Multi-track editing
* Music auto-selection
* Emotion detection
* Face detection / auto framing

---

## 13. Key Challenges

* Accurate timestamp selection
* Preventing LLM hallucination
* Fast video processing
* Good retrieval quality

---

## 14. Development Plan

Phase 1:

* Ingestion + transcription

Phase 2:

* Embeddings + retrieval

Phase 3:

* LLM planner (JSON output)

Phase 4:

* FFmpeg execution

Phase 5:

* CLI + polish

---

## 15. Definition of Done (MVP)

User can:

1. Add clips
2. Enter prompt
3. Get auto-generated video

---

END OF SPEC
