"""Tool to create a new workflow."""

from __future__ import annotations

from typing import Any

from n8n_client.api_client import N8NClient


def run(client: N8NClient, workflow_data: dict[str, Any]) -> dict[str, Any]:
    """Create a workflow via n8n API."""

    return client.create_workflow(workflow_data)
