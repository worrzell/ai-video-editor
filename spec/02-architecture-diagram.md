# Architecture Diagram — AI Video Editor

## System Overview

The diagram below illustrates the end-to-end architecture of the AI Video Editor platform across Web, Mobile, Cloud Run, AI inference providers, and persistent storage.

```mermaid
flowchart TD
    subgraph Clients ["Client Layer"]
        W["Web UI (Responsive HTML5 / CSS3 / Vanilla JS)"]
        M["Mobile App (Expo / React Native 0.76)"]
        C["CLI (Typer / Moon Workspace)"]
    end

    subgraph Security ["Authentication & Protection"]
        JWT["JWT Bearer / HttpOnly Cookie Auth"]
        Cap["Cloud Run Spend Cap (Budget Target)"]
        KS["Automated Billing Killswitch (Cloud Function Gen2)"]
    end

    subgraph CloudRun ["Google Cloud Run (asia-south1, Max Instances: 1, Concurrency: 80)"]
        FE["Google Frontend (GFE)"]
        API["FastAPI Backend (backend/api/server.py)"]
        
        subgraph Services ["Core Processing Services"]
            UP["Chunked Upload Service (/api/upload/chunk)"]
            PROG["5-Step Render Progress Tracker"]
            ING["Ingestion & Metadata Extraction (FFprobe)"]
            TR["Speech-to-Text Transcription (Whisper AI)"]
            EMB["Semantic Embedding (all-MiniLM-L6-v2)"]
            VEC["Vector Store & Retrieval (FAISS)"]
            PLAN["Edit Planner (backend/services/planner.py)"]
            EXEC["Video Execution Engine (backend/services/executor.py)"]
        end

        subgraph LocalScratch ["Local Container RAM / Ephemeral Disk"]
            TMP["/tmp/render_temp_* (High-Speed FFmpeg Segment Scratch)"]
        end
    end

    subgraph AI ["AI Inference Engines"]
        GEM["Google Gemini API (gemini-3.8-flash)"]
        OLL["Local Ollama (llama3) [Offline Mode]"]
    end

    subgraph Storage ["Persistent Storage (GCS Bucket: ai-video-editor-data-512009 via gcsfuse)"]
        DB[("Persistent SQLite: /app/data/app.db")]
        CLIPS["Clips: /app/data/clips/"]
        TRANS["Transcripts: /app/data/transcripts/"]
        OUT["Rendered Final Output: /app/data/outputs/final.mp4"]
    end

    %% Client Interactions
    W -->|Chunked Upload & 30s Polling| FE
    M -->|Chunked Upload & 30s Polling| FE
    C -->|Local Processing| API
    FE --> API
    API --> JWT
    API --> UP
    API --> PROG

    %% Pipeline Flow
    UP --> CLIPS
    API --> ING
    ING --> CLIPS
    ING --> TR
    TR --> TRANS
    TRANS --> EMB
    EMB --> VEC
    API --> PLAN
    VEC --> PLAN
    PLAN -->|Structured Prompt| GEM
    PLAN -.->|Fallback / Local| OLL
    PLAN --> EXEC
    
    %% Execution & Assembly
    CLIPS --> EXEC
    EXEC -->|Fast Random-Access MP4 Writes| TMP
    TMP -->|Concatenate Final Video| OUT
    EXEC --> DB
    PROG --> API

    %% Safety & Spend Net
    Cap -.->|Pause on limit| CloudRun
    KS -.->|Unlink billing on exceed| CloudRun
```

---

## Component Details

### 1. Client Layer
- **Web UI**: Built with modern responsive HTML/CSS/JS. Supports drag-and-drop chunked uploads (20 MB chunks), live 5-step progress visualization, and automatic polling recovery when closing and reopening tabs.
- **Mobile App**: Cross-platform iOS/Android app built with Expo SDK 52 and React Native 0.76. Features native video picking (`expo-image-picker`), keychain auth (`expo-secure-store`), and native sharing (`expo-sharing`).
- **CLI**: Typer-based command line workflow for offline developer usage and batch processing.

### 2. Google Cloud Run Engine
- **Single-Instance Hard Ceiling (`--max-instances 1`)**: Ensures the container never auto-scales into multiple instances, eliminating the risk of unexpected cloud compute bills.
- **Scale-to-Zero (`--min-instances 0`)**: Automatically shuts down container instances when idle, incurring ₹0 / $0 compute costs.
- **80-Slot Container Concurrency**: Allows static asset delivery and 30-second progress polls to be served with zero latency and zero HTTP 429 drops while long-running renders execute.

### 3. Scratch Disk vs. Persistent Storage Isolation
- **Local Scratch (`/tmp`)**: Intermediate FFmpeg video segments are trimmed and processed in local container storage. This eliminates `BufferedWriteHandler.OutOfOrderError` and network latency from Cloud Storage FUSE.
- **Persistent Storage (`/app/data`)**: Cloud Storage bucket mounted via `gcsfuse` ensures that SQLite database records, uploaded source clips, transcripts, and final rendered videos persist indefinitely across container restarts.

### 4. Dual AI Planning
- **Cloud Mode**: Google Gemini API (`gemini-3.8-flash`) provides sub-second structured JSON edit plan generation with high reasoning capacity.
- **Offline Mode**: Ollama (`llama3`) allows the entire pipeline to function completely disconnected from the internet.
