"""Tool to list workflows."""

from __future__ import annotations

from n8n_client.api_client import N8NClient


def run(client: N8NClient) -> list[dict]:
    """List all workflows via n8n API."""

    return client.list_workflows()
