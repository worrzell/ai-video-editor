import base64
import json
import logging
import os
from googleapiclient import discovery

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def stop_billing(event, context):
    """Cloud Function entry point triggered by Pub/Sub budget alert message."""
    try:
        if 'data' not in event:
            logger.warning("No data found in event payload.")
            return

        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(pubsub_message)
        logger.info(f"Received budget alert notification: {data}")

        cost_amount = float(data.get('costAmount', 0.0))
        budget_amount = float(data.get('budgetAmount', 1.0))
        project_id = os.getenv('GCP_PROJECT_ID', 'ai-video-editor-512009')

        logger.info(f"Project: {project_id} | Cost: {cost_amount} | Budget: {budget_amount}")

        # If cost has reached or exceeded threshold (e.g. >= budget or > 0.01), disable billing
        if cost_amount >= budget_amount or cost_amount > 0.01:
            logger.warning(
                f"🚨 COST BREACH DETECTED: Cost ({cost_amount}) >= Threshold ({budget_amount}). "
                f"Disabling billing on project '{project_id}' immediately!"
            )
            service = discovery.build('cloudbilling', 'v1', cache_discovery=False)
            project_name = f'projects/{project_id}'

            # Setting billingAccountName to an empty string disables billing on the project
            billing_info = service.projects().updateBillingInfo(
                name=project_name,
                body={'billingAccountName': ''}
            ).execute()

            logger.warning(f"Billing successfully unlinked: {billing_info}")
        else:
            logger.info(f"Cost ({cost_amount}) is within safe limits. No action taken.")

    except Exception as exc:
        logger.error(f"Error executing stop_billing: {exc}")
        raise exc
