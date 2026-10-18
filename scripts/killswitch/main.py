import base64
import json
import logging
import os
from googleapiclient import discovery

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def stop_billing(event, context):
    """Cloud Function entry point triggered by Pub/Sub budget alert message.
    
    Supports both:
    1. Project-level spend cap (unlinks target project).
    2. Account / Org-level spend cap (unlinks ALL projects under the billing account).
    """
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
        billing_account_id = os.getenv('BILLING_ACCOUNT_ID')
        unlink_all = os.getenv('UNLINK_ALL_PROJECTS', 'false').lower() == 'true'

        logger.info(f"Project: {project_id} | Cost: {cost_amount} | Budget: {budget_amount}")

        # If cost has reached or exceeded threshold (e.g. >= budget or > 0.01), disable billing
        if cost_amount >= budget_amount or cost_amount > 0.01:
            logger.warning(
                f"🚨 COST BREACH DETECTED: Cost ({cost_amount}) >= Threshold ({budget_amount}). "
                f"Executing billing disable procedure..."
            )
            service = discovery.build('cloudbilling', 'v1', cache_discovery=False)

            # Option A: Account-wide / Org-level disable (unlink all projects under billing account)
            if unlink_all and billing_account_id:
                clean_acct = billing_account_id.replace('billingAccounts/', '')
                logger.warning(f"Unlinking ALL projects under billing account: {clean_acct}")
                try:
                    request = service.billingAccounts().projects().list(name=f'billingAccounts/{clean_acct}')
                    while request is not None:
                        response = request.execute()
                        for p in response.get('projectBillingInfo', []):
                            p_id = p.get('projectId')
                            if p_id and p.get('billingEnabled', False):
                                logger.warning(f"Disabling billing on project: {p_id}")
                                service.projects().updateBillingInfo(
                                    name=f'projects/{p_id}',
                                    body={'billingAccountName': ''}
                                ).execute()
                        request = service.billingAccounts().projects().list_next(previous_request=request, previous_response=response)
                    logger.warning("All projects successfully unlinked from billing account.")
                    return
                except Exception as exc:
                    logger.error(f"Failed to unlink all projects: {exc}. Falling back to target project...")

            # Option B: Target project unlink
            project_name = f'projects/{project_id}'
            logger.warning(f"Disabling billing on project '{project_name}'...")
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
