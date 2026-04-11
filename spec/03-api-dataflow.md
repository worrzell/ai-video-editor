# API and Data Flow Diagram

## Overview

This diagram shows how the UI layer, backend services, and data storage interact through API endpoints and CLI commands.

```mermaid
flowchart LR
    subgraph UI[User Interface]
      UI1[CLI / Frontend]
      UI2[Prompt Input]
      UI3[Clip Upload / Selection]
      UI4[Render Trigger]
      UI1 --> UI2
      UI1 --> UI3
      UI1 --> UI4
    end

    subgraph API[Backend API / CLI]
      A1[POST /ingest]
      A2[POST /process]
      A3[POST /generate]
      A4[POST /render]
      A1 --> B1[Ingestion Service]
      A2 --> B2[Media Processing]
      A3 --> B3[LLM Planner]
      A4 --> B4[Execution Engine]
    end

    subgraph Backend[Backend Services]
      B1
      B2
      B3
      B4
      B5[Vector Store / FAISS]
      B6[Transcription / Whisper]
      B7[Embedding Service]
      B8[FFmpeg Runner]
    end

    subgraph Data[Data Storage]
      D1[Raw Clips]
      D2[Transcripts]
      D3[Embeddings]
      D4[Edit Plans]
      D5[Output Video]
    end

    UI3 -->|upload clips| A1
    UI2 -->|enter prompt| A3
    UI4 -->|start render| A4

    B1 --> D1
    B1 --> B2
    B2 --> B6
    B2 --> B7
    B6 --> D2
    B7 --> D3
    B7 --> B5
    B3 --> D4
    B4 --> D5

    A2 --> B2
    B3 --> B5
    B4 --> B8
    B8 --> D5

    D4 -->|plan file| B4
    UI1 -->|view plan| D4
``` 

## Components

- `CLI / Frontend` — sends ingest/process/generate/render requests through API or CLI.
- `POST /ingest` — registers clip sources and triggers ingestion.
- `POST /process` — runs transcription and embedding pipeline.
- `POST /generate` — creates an edit plan from prompt and retrieved segments.
- `POST /render` — executes the final render pipeline and creates output video.
- `Vector Store / FAISS` — stores embeddings and supports retrieval.
- `Transcription / Whisper` — transcribes clip audio to text segments.
- `Embedding Service` — converts text into vectors for retrieval.
- `FFmpeg Runner` — trims, concatenates, and renders video segments.

## Notes

- This spec assumes a unified CLI and API design where CLI commands call the same backend service logic.
- The diagram is intentionally high-level and focused on data movement between UI, API, and storage.
