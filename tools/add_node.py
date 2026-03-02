"""Tool to add a node to an existing workflow."""

from __future__ import annotations

from agent.workflow_builder import WorkflowBuilder
from n8n_client.api_client import N8NClient
from n8n_client.models import N8NWorkflow


def run(
    client: N8NClient,
    builder: WorkflowBuilder,
    workflow_id: str,
    node_type: str,
    after_node: str,
) -> dict:
    """Add a node to a workflow and update it in n8n."""

    raw_workflow = client.get_workflow(workflow_id)
    workflow = N8NWorkflow.model_validate(raw_workflow)
    updated = builder.add_node_to_workflow(
        workflow=workflow,
        node_type=node_type,
        after_node=after_node,
    )
    return client.update_workflow(workflow_id, updated.model_dump(exclude_none=True))
