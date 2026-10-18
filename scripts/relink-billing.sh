#!/usr/bin/env bash
# ==============================================================================
# AI Video Editor — Relink Billing Account after Killswitch
# Usage: bash scripts/relink-billing.sh [PROJECT_ID] [BILLING_ACCOUNT_ID]
# ==============================================================================

set -euo pipefail

TARGET_PROJECT="${1:-${GCP_PROJECT_ID:-ai-video-editor-512009}}"
BILLING_ACCOUNT_ID="${2:-}"

if [ -z "${BILLING_ACCOUNT_ID}" ]; then
  BILLING_ACCOUNT_ID=$(gcloud beta billing accounts list --filter="open=true" --format="value(name)" --limit=1 2>/dev/null || true)
fi

if [ -z "${BILLING_ACCOUNT_ID}" ]; then
  echo "Usage: bash scripts/relink-billing.sh [PROJECT_ID] <BILLING_ACCOUNT_ID>"
  echo "Available billing accounts:"
  gcloud beta billing accounts list
  exit 1
fi

CLEAN_ACCT="${BILLING_ACCOUNT_ID##*/}"

if [ "${TARGET_PROJECT}" = "--all" ]; then
  echo "Relinking billing account '${CLEAN_ACCT}' to ALL projects..."
  PROJECTS=$(gcloud projects list --format="value(projectId)")
  for p in ${PROJECTS}; do
    echo "Linking billing to ${p}..."
    gcloud beta billing projects link "${p}" --billing-account="${CLEAN_ACCT}" || true
  done
  echo "✅ Done relinking all projects."
else
  echo "Relinking billing account '${CLEAN_ACCT}' to project '${TARGET_PROJECT}'..."
  gcloud beta billing projects link "${TARGET_PROJECT}" --billing-account="${CLEAN_ACCT}"
  echo "✅ Billing successfully re-linked to ${TARGET_PROJECT}."
fi
