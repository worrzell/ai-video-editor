# Copilot Instructions for AI Video Editor

## Purpose
Provide strict, repo-specific guardrails so the assistant stays focused on this project, respects its architecture, and maintains its zero-cost cloud protections and local-first capabilities.

## Architecture Context
- **Hybrid Platform:** Supports both **Local-First CLI** (Typer, Whisper, FAISS, Ollama) and **Production Cloud Run** (FastAPI, Google Gemini `gemini-3.8-flash`, persistent SQLite on Cloud Storage volume mounts, and Expo/React Native mobile app).
- **Production URL:** `https://ai-video-editor-backend-379657549399.asia-south1.run.app` (`asia-south1`).
- **Zero-Cost Budget Guardrails:**
  - Scale-to-zero compute: `--min-instances 0` (₹0 when idle).
  - Strict instance ceiling: `--max-instances 1` (never increase max instances).
  - Database: Persistent SQLite file on GCS volume mount (`/app/data/app.db`) to avoid Cloud SQL charges.
  - Container Concurrency: Tuned to 80 to prevent HTTP 429 errors.
  - Scratch Disk: FFmpeg intermediate clips MUST be rendered in `/tmp` to avoid GCSFuse latency.
  - Polling Cadence: Client progress polling MUST use non-overlapping 30-second intervals (`setTimeout`, not rapid `setInterval`).

## Do this
- Work only within the `ai-video-editor` workspace and its files.
- Follow the project architecture and specs in the `spec/` folder.
- Ensure each new feature, file, or architectural change has a corresponding spec file in `spec/` or updates existing specs.
- For architecture-level details, create and maintain Mermaid diagrams in `spec/`.
- Prioritize implementing and improving core video editing and AI planning features.
- Respect the toolchain: Python 3.13, FastAPI, Pytest, React Native 0.76.5, Expo SDK 52, TypeScript, FFmpeg.
- Reference actual filenames, endpoints, and symbols in the workspace.
- Preserve all spend protections, killswitch scripts, and budget boundaries.

## Do not do this
- Do not add paid cloud services (e.g., Cloud SQL, memorystore, load balancers) that violate the zero-cost architecture.
- Do not lower polling intervals below 15-30 seconds or introduce rapid `setInterval` loops that cause Cloud Run 429 drops.
- Do not write intermediate temporary video files into `/app/data/outputs` (always use `/tmp`).
- Do not overwrite code blindly without inspecting existing files.
- Do not propose unrelated frameworks or libraries.
