# Implementation Spec: Phase 7 — Zero-Cost GCP Cloud Run Deployment & Automated Killswitch

## Objective

Deploy the AI Video Editor application to Google Cloud Platform under project **`ai-video-editor-512009`** in region **`asia-south1`** (Mumbai, India) with **zero cloud database cost** and a **hard spending cap at ₹1.00**.

---

## Architecture

```
GitHub Actions (push to main)
   │
   ├─► 1. Unit Tests (pytest backend/tests + tsc mobile)
   │
   ├─► 2. Authenticate to GCP (GCP_SA_KEY)
   │
   ├─► 3. Docker Build & Push to Artifact Registry
   │      asia-south1-docker.pkg.dev/ai-video-editor-512009/ai-video-editor/backend:latest
   │
   └─► 4. Deploy Revision to Google Cloud Run (asia-south1)
          ├── Compute: 4 vCPU, 8GiB RAM, timeout 900s
          ├── Idle Cost: ₹0 (--min-instances 0, scales to zero when idle)
          ├── Traffic Spike Cap: --max-instances 1 (never scales past 1 instance)
          ├── Persistent Database: SQLite (/app/data/app.db) on GCS Volume ($0 cost)
          ├── Persistent Media: GCS Bucket (ai-video-editor-data-512009) mounted to /app/data
          └── Public HTTPS endpoint: https://<service-url>.run.app

Safety Net:
   Spend > ₹0.01 ──► Budget Alert ──► Pub/Sub ──► Cloud Function (scripts/killswitch)
   ──► Unlinks Billing (Halts all services immediately)
```

---

## Infrastructure Components

### 1. Google Cloud Run (`ai-video-editor-backend`)
- **Execution Environment:** Gen2 (Second Generation) for Cloud Storage FUSE volume mount.
- **Port:** Dynamically bound to `${PORT:-8080}` via entrypoint `sh -c "exec uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8080}"`.
- **Scaling Limits:**
  - `--min-instances 0`: Zero cost when idle.
  - `--max-instances 1`: Hard ceiling preventing instance multiplication.
- **Resources:** 4 vCPU, 8 GiB RAM, 900s timeout.

### 2. Persistent Storage & Database (GCS Volume Mount)
- **Bucket:** `ai-video-editor-data-512009` mounted at `/app/data`.
- **Database:** SQLite file at `/app/data/app.db`.
  - Persists across container revisions and scale-to-zero cycles.
  - Zero cloud database charges ($0/month).
  - No VPC connectors or database passwords required.
- **Media:** Raw clips, transcripts, and final rendered videos persist in the bucket.

### 3. Cost Protection Controls (Dual Protection)

#### A. Native Cloud Run Spend Cap (Built-in GCP Feature)
- Scoped to service `ai-video-editor-backend` in project `ai-video-editor-512009`.
- When monthly spend reaches 100% of the target budget (e.g. ₹50 or ₹100), Google Cloud **automatically pauses Cloud Run invocations** and prevents further cost accrual.
- Non-destructive: Does not unlink project billing or affect GCS bucket data. Resets automatically on the next billing cycle or via console unpause.

#### B. Automated Billing Killswitch (Pub/Sub + Cloud Function Fallback)
- **Topic:** `billing-killswitch-topic`
- **Function:** `billing-killswitch` (Gen2 Python 3.11)
- **Trigger:** Cloud Billing Budget alert for project `ai-video-editor-512009` with target ₹1.00.
- **Action:** If spend > ₹0.01, unlinks billing account via Google Cloud Billing API as a nuclear safety brake.
- **Recovery:** `bash scripts/relink-billing.sh <BILLING_ACCOUNT_ID>`.

---

## GitHub Secrets Configuration

Only 3 secrets required in GitHub (`Settings → Secrets and variables → Actions`):

| Secret Name | Description | Example / Source |
|---|---|---|
| `GCP_PROJECT_ID` | GCP Project ID | `ai-video-editor-512009` |
| `GCP_SA_KEY` | Service Account JSON Private Key | Content of `scripts/gcp-sa-key.json` |
| `GEMINI_API_KEY` | Google Gemini API Key | From Google AI Studio |

---

## Setup & Deployment Instructions

```bash
# 1. Log in to gcloud CLI
gcloud auth login

# 2. Run automated infrastructure setup
bash scripts/setup-gcp.sh

# 3. Arm the ₹1 Automated Killswitch
bash scripts/setup-killswitch.sh

# 4. Add the 3 secrets to GitHub Repository Secrets
# 5. Push to main — GitHub Actions builds and deploys to Cloud Run!
```
