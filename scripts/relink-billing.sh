#!/usr/bin/env bash
# ==============================================================================
# AI Video Editor — Relink Billing Account after Killswitch
# Usage: bash scripts/relink-billing.sh [BILLING_ACCOUNT_ID]
# ==============================================================================

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-ai-video-editor-512009}"
BILLING_ACCOUNT_ID="${1:-}"

if [ -z "${BILLING_ACCOUNT_ID}" ]; then
  # Try to auto-detect open billing account
  BILLING_ACCOUNT_ID=$(gcloud beta billing accounts list --filter="open=true" --format="value(name)" --limit=1 2>/dev/null || true)
fi

if [ -z "${BILLING_ACCOUNT_ID}" ]; then
  echo "Usage: bash scripts/relink-billing.sh <BILLING_ACCOUNT_ID>"
  echo "Available billing accounts:"
  gcloud beta billing accounts list
  exit 1
fi

echo "Relinking billing account '${BILLING_ACCOUNT_ID}' to project '${PROJECT_ID}'..."
gcloud beta billing projects link "${PROJECT_ID}" --billing-account="${BILLING_ACCOUNT_ID}"
echo "✅ Billing successfully re-linked to ${PROJECT_ID}."
