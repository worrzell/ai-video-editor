#!/usr/bin/env bash
# ==============================================================================
# AI Video Editor — Automated Google Cloud Platform (GCP) Provisioning Script
# Project ID: ai-video-editor-512009
# Region:     asia-south1 (Mumbai)
# ==============================================================================

set -euo pipefail

# Configuration with defaults
PROJECT_ID="${GCP_PROJECT_ID:-ai-video-editor-512009}"
REGION="${GCP_REGION:-asia-south1}"
REPO_NAME="${GCP_REPO_NAME:-ai-video-editor}"
BUCKET_NAME="${GCP_BUCKET_NAME:-ai-video-editor-data-512009}"
DB_INSTANCE="${GCP_DB_INSTANCE:-ai-video-editor-db}"
DB_NAME="${GCP_DB_NAME:-ai_video_editor}"
DB_USER="${GCP_DB_USER:-editor_app}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 16)}"
SA_NAME="${GCP_SA_NAME:-github-actions-deployer}"
KEY_OUTPUT="scripts/gcp-sa-key.json"

echo "=================================================================="
echo "🚀 Starting GCP Infrastructure Provisioning"
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
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
  sqladmin.googleapis.com \
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

# 4. Create Google Cloud Storage Bucket for Video Data
echo "Configuring Cloud Storage Bucket for persistent video data..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
  echo "✅ Created GCS Bucket: gs://${BUCKET_NAME}"
else
  echo "ℹ️ GCS Bucket gs://${BUCKET_NAME} already exists."
fi

# 5. Create Cloud SQL PostgreSQL Instance
echo "Configuring Cloud SQL (PostgreSQL 16)..."
if ! gcloud sql instances describe "${DB_INSTANCE}" >/dev/null 2>&1; then
  echo "Creating Cloud SQL instance '${DB_INSTANCE}' (this may take 3-5 minutes)..."
  gcloud sql instances create "${DB_INSTANCE}" \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region="${REGION}" \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=02:00
  echo "✅ Created Cloud SQL instance: ${DB_INSTANCE}"
else
  echo "ℹ️ Cloud SQL instance ${DB_INSTANCE} already exists."
fi

# Create Database inside instance
if ! gcloud sql databases describe "${DB_NAME}" --instance="${DB_INSTANCE}" >/dev/null 2>&1; then
  gcloud sql databases create "${DB_NAME}" --instance="${DB_INSTANCE}"
  echo "✅ Created database: ${DB_NAME}"
fi

# Create Database User
if ! gcloud sql users list --instance="${DB_INSTANCE}" --format="value(name)" | grep -w "${DB_USER}" >/dev/null 2>&1; then
  gcloud sql users create "${DB_USER}" \
    --instance="${DB_INSTANCE}" \
    --password="${DB_PASSWORD}"
  echo "✅ Created database user '${DB_USER}' with password."
else
  echo "ℹ️ Database user ${DB_USER} already exists."
fi

INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe "${DB_INSTANCE}" --format="value(connectionName)")
echo "Database Connection Name: ${INSTANCE_CONNECTION_NAME}"

# 6. Create Service Account for GitHub Actions
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
  "roles/cloudsql.client"
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
echo "=================================================================="
echo ""
echo "📋 Required GitHub Repository Secrets to add:"
echo "   Go to: https://github.com/worrzell/ai-video-editor/settings/secrets/actions"
echo ""
echo "1. GCP_PROJECT_ID:     ${PROJECT_ID}"
echo "2. GCP_SA_KEY:         (Copy the entire contents of ${KEY_OUTPUT})"
echo "3. GEMINI_API_KEY:     (Your Google AI Studio Gemini API Key)"
echo "4. AUTH_JWT_SECRET:    $(openssl rand -hex 32)"
echo "5. DB_PASSWORD:        ${DB_PASSWORD}"
echo "6. DB_CONNECTION_NAME: ${INSTANCE_CONNECTION_NAME}"
echo ""
echo "After adding these secrets, any push to 'main' will automatically build and deploy to Cloud Run!"
