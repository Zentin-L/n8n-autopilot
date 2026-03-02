"""Tool to update an existing workflow."""

from __future__ import annotations

from typing import Any

from n8n_client.api_client import N8NClient


def run(
    client: N8NClient, workflow_id: str, workflow_data: dict[str, Any]
) -> dict[str, Any]:
    """Update a workflow via n8n API."""

    return client.update_workflow(workflow_id=workflow_id, workflow_data=workflow_data)
