"""Tool to delete a workflow."""

from __future__ import annotations

from n8n_client.api_client import N8NClient


def run(client: N8NClient, workflow_id: str) -> bool:
    """Delete a workflow via n8n API."""

    return client.delete_workflow(workflow_id=workflow_id)
