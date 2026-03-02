"""Tool to execute a workflow manually."""

from __future__ import annotations

from typing import Any

from n8n_client.api_client import N8NClient


def run(
    client: N8NClient, workflow_id: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute a workflow via n8n API."""

    return client.execute_workflow(workflow_id=workflow_id, data=data)
