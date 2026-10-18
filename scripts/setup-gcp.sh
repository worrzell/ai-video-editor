#!/usr/bin/env bash
# ==============================================================================
# AI Video Editor — Automated Google Cloud Platform (GCP) Provisioning Script
# Zero-Cost Setup: Cloud Run + Persistent SQLite on GCS Volume
# Project ID: ai-video-editor-512009
# Region:     asia-south1 (Mumbai)
# ==============================================================================

set -euo pipefail

# Configuration with defaults
PROJECT_ID="${GCP_PROJECT_ID:-ai-video-editor-512009}"
REGION="${GCP_REGION:-asia-south1}"
REPO_NAME="${GCP_REPO_NAME:-ai-video-editor}"
BUCKET_NAME="${GCP_BUCKET_NAME:-ai-video-editor-data-512009}"
SA_NAME="${GCP_SA_NAME:-github-actions-deployer}"
KEY_OUTPUT="scripts/gcp-sa-key.json"

echo "=================================================================="
echo "🚀 Starting GCP Infrastructure Provisioning (Zero-Cost SQLite Setup)"
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Storage:  gs://${BUCKET_NAME} (Persistent SQLite & Video Data)"
echo "=================================================================="

# 1. Verify gcloud authentication
echo "Checking gcloud authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [ -z "${CURRENT_ACCOUNT}" ]; then
  echo "❌ No active gcloud account found. Please run 'gcloud auth login' first."
  exit 1
fi
echo "✅ Logged in as: ${CURRENT_ACCOUNT}"

# Set default project
gcloud config set project "${PROJECT_ID}"

# 2. Enable necessary GCP APIs
echo "Enabling required GCP services..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  cloudbuild.googleapis.com

echo "✅ APIs enabled."

# 3. Create Artifact Registry Repository
echo "Configuring Artifact Registry..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="AI Video Editor container repository"
  echo "✅ Created Artifact Registry: ${REPO_NAME}"
else
  echo "ℹ️ Artifact Registry ${REPO_NAME} already exists."
fi

# 4. Create Google Cloud Storage Bucket for Persistent SQLite & Video Data
echo "Configuring Cloud Storage Bucket (gs://${BUCKET_NAME})..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
  echo "✅ Created GCS Bucket: gs://${BUCKET_NAME}"
else
  echo "ℹ️ GCS Bucket gs://${BUCKET_NAME} already exists."
fi

# 5. Create Service Account for GitHub Actions
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "Configuring Service Account: ${SA_EMAIL}..."

if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="GitHub Actions Deployer"
  echo "✅ Created Service Account: ${SA_EMAIL}"
else
  echo "ℹ️ Service Account ${SA_EMAIL} already exists."
fi

# Assign required IAM roles to the Service Account
ROLES=(
  "roles/run.admin"
  "roles/artifactregistry.writer"
  "roles/storage.admin"
  "roles/iam.serviceAccountUser"
)

for role in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" \
    --condition=None >/dev/null 2>&1
done
echo "✅ Assigned IAM roles to ${SA_EMAIL}."

# Generate Key file for GitHub Actions Secret
mkdir -p scripts
rm -f "${KEY_OUTPUT}"
gcloud iam service-accounts keys create "${KEY_OUTPUT}" \
  --iam-account="${SA_EMAIL}"
echo "✅ Generated Service Account key at: ${KEY_OUTPUT}"

echo "=================================================================="
echo "🎉 GCP Infrastructure Provisioning Completed Successfully!"
echo "Database: SQLite at /app/data/app.db (zero cloud database charges)"
echo "=================================================================="
echo ""
echo "📋 Required GitHub Repository Secrets to add:"
echo "   Go to: https://github.com/worrzell/ai-video-editor/settings/secrets/actions"
echo ""
echo "1. GCP_PROJECT_ID:     ${PROJECT_ID}"
echo "2. GCP_SA_KEY:         (Copy the entire contents of ${KEY_OUTPUT})"
echo "3. GEMINI_API_KEY:     (Your Google AI Studio Gemini API Key)"
echo "4. AUTH_JWT_SECRET:    $(openssl rand -hex 32)"
echo ""
echo "🛡️ To arm the ₹1 Automated Killswitch:"
echo "   bash scripts/setup-killswitch.sh"
