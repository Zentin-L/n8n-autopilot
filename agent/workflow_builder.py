"""Workflow construction utilities converting structured intent into n8n JSON."""

from __future__ import annotations

import uuid
from typing import Any

from agent.node_registry import NODE_REGISTRY
from n8n_client.models import N8NNode, N8NWorkflow


class WorkflowBuilder:
    """Build and modify n8n workflows."""

    def build_from_description(
        self,
        description: str,
        nodes_spec: list[dict[str, Any]],
        workflow_name: str | None = None,
    ) -> N8NWorkflow:
        """Build workflow from a high-level nodes specification."""

        normalized_specs = self._ensure_trigger_node(nodes_spec)
        nodes: list[N8NNode] = []
        positions = self.auto_position_nodes(normalized_specs)

        for idx, spec in enumerate(normalized_specs):
            registry_entry = self._resolve_node_type(spec.get("type", "manual_trigger"))
            parameters = dict(registry_entry.get("defaults", {}))
            parameters.update(spec.get("parameters", {}))
            name = spec.get("name") or f"{spec.get('type', 'node').title()} {idx + 1}"

            nodes.append(
                N8NNode(
                    id=str(uuid.uuid4()),
                    name=name,
                    type=registry_entry["type"],
                    typeVersion=float(spec.get("typeVersion", 1)),
                    position=positions[idx],
                    parameters=parameters,
                    credentials=spec.get("credentials"),
                )
            )

        connections = self.create_connections([node.name for node in nodes])
        return N8NWorkflow(
            name=workflow_name or self._name_from_description(description),
            nodes=nodes,
            connections=connections,
            active=False,
            settings={},
            tags=[],
        )

    def auto_position_nodes(self, nodes: list[dict[str, Any]]) -> list[list[int]]:
        """Arrange nodes in a left-to-right readable flow layout."""

        x_start = 240
        y = 300
        x_gap = 280
        return [[x_start + x_gap * index, y] for index, _ in enumerate(nodes)]

    def create_connections(self, node_sequence: list[str]) -> dict[str, Any]:
        """Auto-connect nodes in sequence.

        n8n stores connections as:
        {sourceNode: {"main": [[{"node": target, "type": "main", "index": 0}]]}}
        where each source node may have multiple outputs (outer list) and each output can
        connect to multiple targets (inner list). For simple linear workflows, we only use
        a single output with one target.
        """

        connections: dict[str, Any] = {}
        for current_node, next_node in zip(node_sequence, node_sequence[1:]):
            connections[current_node] = {
                "main": [[{"node": next_node, "type": "main", "index": 0}]]
            }
        return connections

    def add_node_to_workflow(
        self,
        workflow: N8NWorkflow,
        node_type: str,
        after_node: str,
    ) -> N8NWorkflow:
        """Insert a node in an existing workflow after a named node."""

        target_index = next(
            (idx for idx, node in enumerate(workflow.nodes) if node.name == after_node),
            None,
        )
        if target_index is None:
            raise ValueError(f"Node '{after_node}' not found in workflow")

        registry_entry = self._resolve_node_type(node_type)
        new_node = N8NNode(
            id=str(uuid.uuid4()),
            name=f"{node_type.title()} Added",
            type=registry_entry["type"],
            typeVersion=1.0,
            position=[0, 0],
            parameters=dict(registry_entry.get("defaults", {})),
            credentials=None,
        )

        updated_nodes = list(workflow.nodes)
        updated_nodes.insert(target_index + 1, new_node)
        updated_positions = self.auto_position_nodes([{"name": n.name} for n in updated_nodes])

        for idx, node in enumerate(updated_nodes):
            node.position = updated_positions[idx]

        connections = self.create_connections([node.name for node in updated_nodes])
        return workflow.model_copy(
            update={"nodes": updated_nodes, "connections": connections},
            deep=True,
        )

    def _ensure_trigger_node(self, nodes_spec: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not nodes_spec:
            return [{"type": "manual_trigger", "name": "Manual Trigger", "parameters": {}}]

        trigger_types = {
            NODE_REGISTRY["manual_trigger"]["type"],
            NODE_REGISTRY["webhook_trigger"]["type"],
            NODE_REGISTRY["cron_trigger"]["type"],
            NODE_REGISTRY["error_trigger"]["type"],
        }
        first_type = self._resolve_node_type(nodes_spec[0].get("type", "manual_trigger"))["type"]
        if first_type in trigger_types:
            return nodes_spec

        return [{"type": "manual_trigger", "name": "Manual Trigger", "parameters": {}}] + nodes_spec

    @staticmethod
    def _name_from_description(description: str) -> str:
        base = description.strip().split(".")[0][:60]
        return base or "AI Generated Workflow"

    @staticmethod
    def _resolve_node_type(node_type_or_key: str) -> dict[str, Any]:
        if node_type_or_key in NODE_REGISTRY:
            return NODE_REGISTRY[node_type_or_key]

        for _, entry in NODE_REGISTRY.items():
            if entry["type"] == node_type_or_key:
                return entry

        raise ValueError(f"Unsupported node type: {node_type_or_key}")
