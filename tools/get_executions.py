"""Tool to fetch execution history."""

from __future__ import annotations

from n8n_client.api_client import N8NClient


def run(client: N8NClient, workflow_id: str | None = None) -> list[dict]:
    """Get execution history via n8n API."""

    return client.get_executions(workflow_id=workflow_id)
