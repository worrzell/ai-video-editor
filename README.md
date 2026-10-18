# AI Video Editing Tool (Local-First)

A fully offline AI-powered video editing tool that accepts multiple video clips and a natural language prompt to automatically generate rough-cut edited videos using local models.

## Features

- **Local-First:** Runs entirely offline using local models (Whisper, FAISS, Ollama)
- **Multi-Clip Ingestion:** Process multiple video files and extract metadata
- **AI Transcription:** Automatic speech-to-text with Whisper
- **Semantic Retrieval:** Vector-based search to find relevant clip segments
- **LLM Planning:** Generates structured edit plans using local LLMs (Ollama)
- **FFmpeg Rendering:** Concatenates and renders final video with aspect ratio support
- **DaVinci Resolve Integration:** Optional advanced rendering with professional color grading and effects
- **CLI Interface:** Simple command-line workflow

## Quick Start

### 1. Installation

Clone the repository and install dependencies using Poetry and the root Moon workspace:

```bash
git clone <repo_url>
cd ai-video-editor
poetry install
```

If you want to use Moon tasks from the workspace root instead of calling Poetry directly:

```bash
moon run backend:install
```

This installs dependencies based on `pyproject.toml` and creates a local Poetry-managed virtual environment.

If Poetry is not installed, follow the Poetry installation instructions at https://python-poetry.org/docs/#installation.

### 2. Install System Dependencies

**Ollama (for LLM inference):**
```bash
# Visit https://ollama.ai and download the installer
# Or on macOS: brew install ollama
ollama pull llama3  # Pull the model
ollama serve        # Start the Ollama server (keep running in background)
```

**FFmpeg:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
choco install ffmpeg
```

**DaVinci Resolve (Optional for Advanced Rendering):**
```bash
# Install DaVinci Resolve Studio (paid version required for command-line rendering)
# Download from: https://www.blackmagicdesign.com/products/davinciresolve

# The web UI includes a checkbox to use DaVinci Resolve for final rendering
# This provides professional color grading, effects, and higher quality output
```

### 3. Prepare Your Video Clips

Place video clips in `data/clips/`:
```bash
mkdir -p data/clips
cp your_videos/*.mp4 data/clips/
```

## Web UI (New)

Start the web interface from the repository root using Poetry:

```bash
poetry run uvicorn backend.api.server:app --reload --host 0.0.0.0 --port 8000
```

Or use Moon:

```bash
moon run backend:web
```

Then open `http://localhost:8000` in your browser.

If you need to pass CLI arguments through the root task, use:

```bash
moon run backend:dev -- ingest ./data/clips/
```

## Mobile App (Expo / React Native)

Cross-platform iOS + Android app inside `mobile/` with a 4-tab bottom navigation bar.

### Prerequisites

- [Node.js 20+](https://nodejs.org/)
- [Expo Go](https://expo.dev/go) app installed on your iOS or Android device (or use an emulator)
- Backend running (see Web UI section above)

### Setup

```bash
cd mobile
cp .env.example .env
# Edit .env — set EXPO_PUBLIC_API_BASE_URL:
#   iOS Simulator:     http://localhost:8000
#   Android Emulator:  http://10.0.2.2:8000
#   Physical device:   http://<your-LAN-IP>:8000

npm install
npx expo start
```

Scan the QR code with **Expo Go** on your device, or press `i` (iOS Simulator) / `a` (Android Emulator).

Or use Moon from the repo root:

```bash
moon run mobile:start
```

### Tabs

| Tab | Purpose |
|---|---|
| 🎬 **Upload** | Pick videos from camera roll → upload to backend |
| ✨ **Render** | Enter a prompt, toggle options, generate edit plan & render |
| 📁 **Library** | View uploaded clips, download & share the final video |
| 👤 **Profile** | Sign in / register / log out, view server info |

---


## Complete Workflow

### Phase 1: Ingest & Transcribe

```bash
# Scan and extract metadata from video clips
python backend/main.py ingest ./data/clips/

# Transcribe all clips using Whisper
python backend/main.py process --whisper-model small
```

**Output:**
- `data/clips_manifest.json` — metadata for all clips
- `data/transcripts/` — JSON files with segment-level transcripts

### Phase 2: Build Index & Search

```bash
# Build FAISS index from transcripts
python backend/main.py index --embedding-model all-MiniLM-L6-v2

# (Optional) Search for specific keywords
python backend/main.py search "create a highlight reel" --top-k 5
```

**Output:**
- `data/embeddings.index` — FAISS search index
- `data/embeddings.meta.json` — segment metadata and embeddings

### Phase 3: Generate Edit Plan

```bash
# Use LLM to generate edit plan from natural language prompt
python backend/main.py plan "create a cinematic highlight reel with fast pacing"
```

**Output:**
- `data/edit_plan.json` — structured JSON plan with clip timeline and style

**Example Plan:**
```json
{
  "timeline": [
    {"clip_id": "clip_001", "start": 12.3, "end": 25.0, "reason": "exciting moment"},
    {"clip_id": "clip_002", "start": 5.1, "end": 18.5, "reason": "key highlight"}
  ],
  "style": {
    "pace": "fast",
    "captions": false,
    "aspect_ratio": "16:9"
  }
}
```

### Phase 4: Render Video

```bash
# Render the final video
python backend/main.py render

# Or with custom output path
python backend/main.py render --output-path ./my_video.mp4
```

**Output:**
- `data/outputs/final.mp4` — final edited video

## CLI Reference

### ingest
Scan and extract metadata from video clips.
```bash
python backend/main.py ingest ./data/clips/
```

### process
Transcribe clips using Whisper.
```bash
python backend/main.py process \
  --clips-dir ./data/clips/ \
  --transcripts-dir ./data/transcripts/ \
  --whisper-model small \
  --language en
```

### index
Build FAISS index from transcripts.
```bash
python backend/main.py index \
  --transcripts-dir ./data/transcripts/ \
  --embedding-model all-MiniLM-L6-v2
```

### search
Search the FAISS index.
```bash
python backend/main.py search "your prompt here" \
  --top-k 5 \
  --embedding-model all-MiniLM-L6-v2
```

### plan
Generate edit plan using LLM.
```bash
python backend/main.py plan "your edit request" \
  --top-k 5 \
  --embedding-model all-MiniLM-L6-v2 \
  --ollama-model llama3
```

### render
Render video from edit plan.
```bash
python backend/main.py render \
  --edit-plan-path ./data/edit_plan.json \
  --clips-dir ./data/clips/ \
  --output-path ./data/outputs/final.mp4
```

## Architecture

See the technical specs in the `spec/` folder:
- [01-core-architecture.md](spec/01-core-architecture.md) — System design
- [02-architecture-diagram.md](spec/02-architecture-diagram.md) — Visual architecture with Mermaid
- [03-api-dataflow.md](spec/03-api-dataflow.md) — API and data flow
- Phases 1-5 implementation specs

## Troubleshooting

### "Ollama model not found"
Make sure Ollama is running and the model is downloaded:
```bash
ollama serve &
ollama pull llama3
```

### "FFmpeg not found"
Install FFmpeg using your package manager (see Installation section).

### "No transcripts found"
Run the `process` command first to generate transcripts from clips.

### "Whisper model too slow"
Use a smaller model:
```bash
python backend/main.py process --whisper-model tiny
```

Options: `tiny`, `base`, `small`, `medium`, `large`

### "FAISS index not found"
Run the `index` command to build the index from transcripts.

## Performance Tips

- **Faster Transcription:** Use `tiny` or `base` Whisper model
- **Faster Embedding:** Use a smaller embedding model (e.g., `all-MiniLM-L6-v2`)
- **Batch Processing:** Process multiple clips together with `process` command
- **Parallel Search:** FAISS searches are fast for 1k-10k segments

## Development

### Install dependencies
```bash
poetry install
```

### Running Tests
```bash
poetry run pytest backend/tests
# or
moon run backend:test
```

### Code Formatting
```bash
poetry run black backend/
poetry run flake8 backend/
# or
moon run backend:format
moon run backend:lint
```

### Running CLI commands through Poetry
```bash
poetry run python backend/main.py ingest ./data/clips/
poetry run python backend/main.py process --whisper-model small
```

### Running CLI commands through Moon
```bash
moon run backend:dev -- ingest ./data/clips/
moon run backend:dev -- process --whisper-model small
```

## Project Structure

```
ai-video-editor/
├── backend/
│   ├── main.py                 # CLI entry point
│   ├── requirements.txt         # Python dependencies
│   ├── services/
│   │   ├── ingestion.py        # Clip ingestion
│   │   ├── transcription.py    # Whisper integration
│   │   ├── embedding.py        # Embedding provider
│   │   ├── indexing.py         # FAISS indexing
│   │   ├── retrieval.py        # Semantic search
│   │   ├── planner.py          # LLM planning
│   │   ├── executor.py         # Video rendering
│   │   └── ffmpeg_runner.py    # FFmpeg operations
│   ├── db/
│   │   └── vector_store.py     # FAISS wrapper
│   ├── models/
│   │   └── edit_plan.py        # Pydantic schemas
│   └── utils/
├── data/
│   ├── clips/                  # Input video clips
│   ├── transcripts/            # Generated transcripts
│   ├── outputs/                # Final rendered video
│   ├── clips_manifest.json     # Metadata manifest
│   ├── embeddings.index        # FAISS index
│   └── edit_plan.json          # Generated plan
├── spec/
│   ├── 01-core-architecture.md
│   ├── 02-architecture-diagram.md
│   ├── 03-api-dataflow.md
│   ├── 04-phase1-ingestion-transcription.md
│   ├── 05-phase2-embeddings-retrieval.md
│   ├── 06-phase3-llm-planning.md
│   ├── 07-phase4-rendering.md
│   └── 08-phase5-polish-integration.md
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| CLI Framework | Typer |
| Transcription | OpenAI Whisper |
| Embeddings | sentence-transformers |
| Vector DB | FAISS |
| LLM Inference | Ollama |
| Video Processing | FFmpeg |
| Data Validation | Pydantic |

## Future Enhancements

- [ ] Web UI for interactive editing
- [ ] Real-time preview of edits
- [ ] Music auto-selection and sync
- [ ] Automatic captions and overlays
- [ ] Face detection for auto-framing
- [ ] Emotion-based clip selection
- [ ] Batch rendering
- [ ] Edit plan templates

## Contributing

Contributions welcome! Please ensure:
1. Code follows existing style
2. All specs are up-to-date
3. Tests pass
4. Documentation is clear

## License

MIT License — See LICENSE file for details.

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the spec files in `spec/` folder
3. Open an issue with detailed logs

---

**Made with ❤️ for local-first AI video editing**
