# API and Data Flow Specification

## Overview

This document specifies the REST API endpoints, request/response contracts, and data movement across the AI Video Editor system.

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Web / Mobile)
    participant Client as Frontend Client
    participant API as FastAPI Backend
    participant Ingest as Ingestion Service
    participant Whisper as Whisper AI
    participant Vector as FAISS Vector Store
    participant Gemini as Google Gemini API
    participant FFmpeg as FFmpeg Runner
    participant Storage as GCS Volume & /tmp

    %% 1. Upload
    User->>Client: Select video clips
    loop Every 20 MB Chunk
        Client->>API: POST /api/upload/chunk
        API->>Storage: Append chunk to temporary part file
    end
    API->>Storage: Assemble final clip into /app/data/clips/
    API-->>Client: 200 OK {"status": "complete", "filename": "clip.mp4"}

    %% 2. Render Request
    User->>Client: Enter edit prompt & click Render
    Client->>API: POST /api/render (prompt, use_resolve)
    API-->>Client: Processing pipeline initiated

    %% 3. Polling Loop
    loop Every 30 Seconds (setTimeout)
        Client->>API: GET /api/render/progress
        API-->>Client: 200 OK {"step": 2, "percent": 35, "step_name": "Transcribing Audio", ...}
    end

    %% Pipeline Steps
    API->>Ingest: Step 1: Scan clips & extract metadata
    API->>Whisper: Step 2: Transcribe speech to segment JSONs
    Whisper->>Storage: Save to /app/data/transcripts/
    API->>Vector: Step 3: Embed segments & retrieve relevant clips
    API->>Gemini: Step 4: Generate EditPlan JSON
    Gemini-->>API: Validated EditPlan timeline
    API->>FFmpeg: Step 5: Trim segments & concatenate
    FFmpeg->>Storage: Write intermediate segments to /tmp (local scratch)
    FFmpeg->>Storage: Write final video to /app/data/outputs/final.mp4
    API->>Storage: Record job in SQLite (/app/data/app.db)

    %% Completion
    Client->>API: GET /api/render/progress
    API-->>Client: 200 OK {"status": "completed", "percent": 100, ...}
    Client->>API: GET /api/download/output
    API-->>Client: Stream final.mp4 video file
```

---

## Detailed API Endpoints

### 1. Authentication Endpoints

#### `POST /api/auth/register`
Creates a new user account.
- **Request Body (JSON):**
  ```json
  {
    "username": "creator",
    "password": "securepassword123"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Account 'creator' created successfully!",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": { "id": "uuid", "username": "creator", "role": "user" }
  }
  ```
- **Cookies:** Sets HttpOnly `access_token` cookie for web clients.

#### `POST /api/auth/login`
Authenticates a user and issues a JWT token.
- **Request Body (JSON):** `{"username": "...", "password": "..."}`
- **Response (200 OK):** Same as register; mobile clients persist the `token` in `expo-secure-store`.

#### `POST /api/auth/logout`
Logs out the user and clears authentication cookies.

#### `GET /api/auth/me`
Returns current session authentication status and database engine.

---

### 2. Media Upload Endpoints

#### `POST /api/upload/chunk`
Uploads files in resilient 20 MB chunks to bypass Cloud Run's 32 MB payload limit.
- **Headers:** `Content-Type: multipart/form-data`, `Authorization: Bearer <token>`
- **Form Fields:**
  - `file`: Binary chunk blob
  - `filename`: e.g., `"drone_shot.mp4"`
  - `chunk_index`: Zero-indexed integer (`0, 1, 2, ...`)
  - `total_chunks`: Total number of parts
- **Response (200 OK):**
  - In-progress chunk: `{"status": "chunk_received", "chunk_index": 0, "total_chunks": 5}`
  - Final chunk: `{"status": "complete", "filename": "drone_shot.mp4", "message": "Successfully uploaded drone_shot.mp4."}`

---

### 3. Render & Progress Endpoints

#### `POST /api/render`
Initiates the AI-driven editing and rendering pipeline.
- **Headers:** `Content-Type: application/x-www-form-urlencoded`, `Authorization: Bearer <token>`
- **Form Fields:**
  - `prompt`: String natural language edit description (e.g. `"create a fast-paced highlight reel"`)
  - `use_resolve`: Boolean flag (`true` to export DaVinci Resolve project, `false` for FFmpeg rendering)
- **Response (200 OK):**
  ```json
  {
    "status": "completed",
    "output_url": "/api/download/output",
    "plan": {
      "timeline": [...],
      "style": { "pace": "fast", "captions": false, "aspect_ratio": "9:16" }
    }
  }
  ```

#### `GET /api/render/progress`
Polls the live status of the rendering pipeline.
- **Polling Cadence:** 30 seconds (`30000ms`) via non-overlapping `setTimeout`.
- **Response (200 OK):**
  ```json
  {
    "status": "processing",
    "step": 3,
    "total_steps": 5,
    "percent": 55,
    "step_name": "Semantic Indexing",
    "message": "Building semantic index and searching relevant segments...",
    "error": null
  }
  ```
- **Lifecycle Statuses:** `idle`, `processing`, `completed`, `failed`.
- **Tab Reopen Support:** If a user closes or refreshes their browser during rendering, `GET /api/render/progress` returns the active step and allows the UI to resume tracking immediately.

---

### 4. Status & Delivery Endpoints

#### `GET /api/status`
Returns service status, list of uploaded clips, and whether a final output exists.
- **Response (200 OK):**
  ```json
  {
    "clips": ["clip1.mp4", "clip2.mov"],
    "output_exists": true,
    "download_url": "/api/download/output",
    "authenticated": true,
    "user": { "username": "creator" },
    "database": "sqlite",
    "model": "gemini-3.8-flash"
  }
  ```

#### `GET /api/download/output`
Streams the final rendered video file (`final.mp4`) as an attachment for browser download or mobile saving.
