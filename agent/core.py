"""Main n8n AI agent orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from agent.llm_engine import AgentResponse, LLMEngine
from agent.prompt_templates import build_system_prompt
from agent.workflow_builder import WorkflowBuilder
from n8n_client.api_client import N8NAPIError, N8NClient
from n8n_client.models import N8NWorkflow
from tools import (
    create_workflow as tool_create_workflow,
    delete_workflow as tool_delete_workflow,
    execute_workflow as tool_execute_workflow,
    get_executions as tool_get_executions,
    list_workflows as tool_list_workflows,
    update_workflow as tool_update_workflow,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PendingAction:
    """Represents a user-confirmed action waiting for approval."""

    action: str
    payload: dict[str, Any]


@dataclass(slots=True)
class AgentTurnResult:
    """Result returned to CLI for display and post-actions."""

    text: str
    pending_action: PendingAction | None = None
    preview_workflow: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] | None = None


class N8NAgent:
    """Agent that plans and manages n8n workflows through LLM tool-calling."""

    def __init__(self) -> None:
        self.client = N8NClient()
        self.builder = WorkflowBuilder()
        self.pending_action: PendingAction | None = None
        self.tools_schema = self._build_tool_schema()
        system_prompt = build_system_prompt(self._tool_descriptions())
        self.llm = LLMEngine(system_prompt=system_prompt)
        self.tool_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "create_workflow": self._tool_create_workflow,
            "list_workflows": self._tool_list_workflows,
            "get_workflow_details": self._tool_get_workflow_details,
            "update_workflow": self._tool_update_workflow,
            "delete_workflow": self._tool_delete_workflow,
            "execute_workflow": self._tool_execute_workflow,
            "get_execution_history": self._tool_get_execution_history,
            "activate_workflow": self._tool_activate_workflow,
            "deactivate_workflow": self._tool_deactivate_workflow,
        }

    def handle_message(self, user_input: str) -> AgentTurnResult:
        """Run full agentic loop for a user message."""

        response = self.llm.process_message(user_input=user_input, tools=self.tools_schema)
        if not isinstance(response, AgentResponse):
            return AgentTurnResult(text="Streaming mode is not supported in this code path.")

        tool_results: list[dict[str, Any]] = []
        preview_workflow: dict[str, Any] | None = None
        pending_action: PendingAction | None = None

        iteration = 0
        while response.tool_calls and iteration < 5:
            outputs = []
            for tool_call in response.tool_calls:
                logger.info("Executing tool call: %s", tool_call.name)
                handler = self.tool_handlers.get(tool_call.name)
                if not handler:
                    output = {"error": f"Unknown tool: {tool_call.name}"}
                else:
                    try:
                        output = handler(tool_call.arguments)
                    except (ValueError, N8NAPIError) as exc:
                        output = {"error": str(exc)}
                    except Exception as exc:
                        output = {"error": f"Unexpected tool error: {exc}"}

                if output.get("preview_workflow"):
                    preview_workflow = output["preview_workflow"]
                if output.get("pending_action"):
                    pending_payload = output["pending_action"]
                    pending_action = PendingAction(
                        action=pending_payload["action"], payload=pending_payload
                    )
                    self.pending_action = pending_action

                outputs.append({"tool_call_id": tool_call.id, "output": output})
                tool_results.append({"tool": tool_call.name, "output": output})

            response = self.llm.submit_tool_results(outputs, self.tools_schema)
            iteration += 1

        return AgentTurnResult(
            text=response.content,
            pending_action=pending_action,
            preview_workflow=preview_workflow,
            tool_results=tool_results,
        )

    def confirm_pending_action(self) -> dict[str, Any]:
        """Execute pending action after user confirmation."""

        if not self.pending_action:
            return {"status": "no_pending_action"}

        action = self.pending_action.action
        payload = self.pending_action.payload
        self.pending_action = None

        if action == "create_workflow":
            workflow_data = payload["workflow_data"]
            created = tool_create_workflow.run(self.client, workflow_data)
            if payload.get("auto_activate") and created.get("id"):
                activation = self.client.activate_workflow(str(created["id"]))
                return {"created": created, "activation": activation}
            return {"created": created}
        if action == "delete_workflow":
            workflow_id = payload["workflow_id"]
            return {"deleted": tool_delete_workflow.run(self.client, workflow_id)}

        return {"status": "unsupported_action", "action": action}

    def clear_memory(self) -> None:
        """Clear LLM conversation history."""

        self.llm.clear_memory()

    def shutdown(self) -> None:
        """Close open resources."""

        self.client.close()

    def _tool_create_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        description = args.get("description", "AI generated workflow")
        nodes_spec = args.get("nodes_spec", [])
        workflow_name = args.get("workflow_name")
        auto_activate = bool(args.get("auto_activate", False))

        workflow = self.builder.build_from_description(
            description=description,
            nodes_spec=nodes_spec,
            workflow_name=workflow_name,
        )
        workflow_data = workflow.model_dump(exclude_none=True)

        result: dict[str, Any] = {
            "status": "pending_confirmation",
            "message": "Workflow preview generated. Awaiting user confirmation before create.",
            "preview_workflow": workflow_data,
            "pending_action": {
                "action": "create_workflow",
                "workflow_data": workflow_data,
                "auto_activate": auto_activate,
            },
        }
        return result

    def _tool_list_workflows(self, args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        workflows = tool_list_workflows.run(self.client)
        return {"workflows": workflows}

    def _tool_get_workflow_details(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")
        workflow = self.client.get_workflow(workflow_id)
        return {"workflow": workflow}

    def _tool_update_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")

        if args.get("add_node"):
            raw = self.client.get_workflow(workflow_id)
            workflow = N8NWorkflow.model_validate(raw)
            updated = self.builder.add_node_to_workflow(
                workflow=workflow,
                node_type=args["add_node"].get("node_type", "set"),
                after_node=args["add_node"].get("after_node", workflow.nodes[-1].name),
            )
            payload = updated.model_dump(exclude_none=True)
        else:
            payload = args.get("workflow_data")
            if not isinstance(payload, dict):
                raise ValueError("workflow_data must be provided as a dict")

        updated_result = tool_update_workflow.run(self.client, workflow_id, payload)
        return {"updated": updated_result}

    def _tool_delete_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")
        return {
            "status": "pending_confirmation",
            "message": f"Delete requested for workflow {workflow_id}. Awaiting confirmation.",
            "pending_action": {"action": "delete_workflow", "workflow_id": workflow_id},
        }

    def _tool_execute_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")

        data = args.get("data")
        execution = tool_execute_workflow.run(self.client, workflow_id, data)
        return {"execution": execution}

    def _tool_get_execution_history(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = args.get("workflow_id")
        executions = tool_get_executions.run(
            self.client, str(workflow_id) if workflow_id else None
        )
        return {"executions": executions}

    def _tool_activate_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")
        return {"activation": self.client.activate_workflow(workflow_id)}

    def _tool_deactivate_workflow(self, args: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(args.get("workflow_id", "")).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required")
        return {"deactivation": self.client.deactivate_workflow(workflow_id)}

    def _tool_descriptions(self) -> str:
        descriptions = [
            "- create_workflow: Build and stage a new workflow from natural language and node specs.",
            "- list_workflows: List all existing workflows.",
            "- get_workflow_details: Retrieve full details for a workflow by ID.",
            "- update_workflow: Update workflow JSON or add node into existing workflow.",
            "- delete_workflow: Request deletion of a workflow (requires user confirmation).",
            "- execute_workflow: Trigger a workflow run manually.",
            "- get_execution_history: Retrieve execution logs/history.",
            "- activate_workflow: Activate a workflow.",
            "- deactivate_workflow: Deactivate a workflow.",
        ]
        return "\n".join(descriptions)

    def _build_tool_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_workflow",
                    "description": "Create a new n8n workflow from natural language intent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "workflow_name": {"type": "string"},
                            "auto_activate": {"type": "boolean"},
                            "nodes_spec": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"},
                                        "name": {"type": "string"},
                                        "parameters": {"type": "object"},
                                        "credentials": {"type": "object"},
                                    },
                                    "required": ["type"],
                                },
                            },
                        },
                        "required": ["description", "nodes_spec"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_workflows",
                    "description": "List all n8n workflows.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_workflow_details",
                    "description": "Get workflow details by workflow ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"workflow_id": {"type": "string"}},
                        "required": ["workflow_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_workflow",
                    "description": "Update a workflow payload or add a node.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_id": {"type": "string"},
                            "workflow_data": {"type": "object"},
                            "add_node": {
                                "type": "object",
                                "properties": {
                                    "node_type": {"type": "string"},
                                    "after_node": {"type": "string"},
                                },
                            },
                        },
                        "required": ["workflow_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_workflow",
                    "description": "Delete a workflow by ID (requires confirmation).",
                    "parameters": {
                        "type": "object",
                        "properties": {"workflow_id": {"type": "string"}},
                        "required": ["workflow_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_workflow",
                    "description": "Execute workflow manually by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_id": {"type": "string"},
                            "data": {"type": "object"},
                        },
                        "required": ["workflow_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_execution_history",
                    "description": "Get execution history; optionally filtered by workflow ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"workflow_id": {"type": "string"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "activate_workflow",
                    "description": "Activate a workflow.",
                    "parameters": {
                        "type": "object",
                        "properties": {"workflow_id": {"type": "string"}},
                        "required": ["workflow_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "deactivate_workflow",
                    "description": "Deactivate a workflow.",
                    "parameters": {
                        "type": "object",
                        "properties": {"workflow_id": {"type": "string"}},
                        "required": ["workflow_id"],
                    },
                },
            },
        ]
