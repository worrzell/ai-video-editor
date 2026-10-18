#!/usr/bin/env bash
# ==============================================================================
# AI Video Editor — GCP Automated Billing Killswitch Setup
# Project: ai-video-editor-512009
# Region:  asia-south1
# ==============================================================================

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-ai-video-editor-512009}"
REGION="${GCP_REGION:-asia-south1}"
TOPIC_NAME="billing-killswitch-topic"
FUNCTION_NAME="billing-killswitch"
SA_NAME="billing-killswitch-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=================================================================="
echo "🛡️ Setting up GCP Automated Billing Killswitch (Hard Cap)"
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "=================================================================="

# Verify active gcloud account
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [ -z "${CURRENT_ACCOUNT}" ]; then
  echo "❌ Please log in to gcloud first: gcloud auth login"
  exit 1
fi

gcloud config set project "${PROJECT_ID}"

# 1. Enable APIs required for Cloud Functions & Billing notifications
echo "Enabling Cloud Functions, Pub/Sub, and Cloud Billing APIs..."
gcloud services enable \
  cloudbilling.googleapis.com \
  pubsub.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com

# 2. Create Pub/Sub Topic
echo "Creating Pub/Sub topic '${TOPIC_NAME}'..."
if ! gcloud pubsub topics describe "${TOPIC_NAME}" >/dev/null 2>&1; then
  gcloud pubsub topics create "${TOPIC_NAME}"
  echo "✅ Created topic: ${TOPIC_NAME}"
else
  echo "ℹ️ Topic ${TOPIC_NAME} already exists."
fi

# 3. Create Service Account for the Killswitch Function
echo "Creating Service Account '${SA_NAME}'..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Billing Killswitch Automated Disabler"
  echo "✅ Created Service Account: ${SA_EMAIL}"
else
  echo "ℹ️ Service Account ${SA_EMAIL} already exists."
fi

# 4. Grant Project-level IAM role to disable billing
echo "Granting roles/billing.projectManager to ${SA_EMAIL}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/billing.projectManager" \
  --condition=None >/dev/null 2>&1

# 5. Deploy Cloud Function (Gen2)
echo "Deploying Cloud Function '${FUNCTION_NAME}'..."
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source=scripts/killswitch \
  --entry-point=stop_billing \
  --trigger-topic="${TOPIC_NAME}" \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --memory=256Mi \
  --timeout=60s

echo "✅ Cloud Function '${FUNCTION_NAME}' deployed successfully."

# 6. Instructions for connecting Cloud Billing Budget to Topic
echo "=================================================================="
echo "🎉 Killswitch Function is Armed & Ready!"
echo "=================================================================="
echo ""
echo "To link your Budget to this Killswitch:"
echo "1. Go to: https://console.cloud.google.com/billing/budgets"
echo "2. Click 'Create Budget' (or edit an existing budget for project ${PROJECT_ID}):"
echo "   - Target Amount: ₹1.00 (or $0.01)"
echo "   - Under 'Manage Notifications':"
echo "     * Check: 'Connect a Pub/Sub topic to this budget'"
echo "     * Select Project: ${PROJECT_ID}"
echo "     * Select Topic: projects/${PROJECT_ID}/topics/${TOPIC_NAME}"
echo "3. Save the budget."
echo ""
echo "Whenever spend exceeds ₹0.01, this function will automatically unlink"
echo "billing from ${PROJECT_ID}, stopping all charges immediately."
echo "=================================================================="
