"""Registry of common n8n nodes for planning workflows."""

from __future__ import annotations

from typing import Any


NODE_REGISTRY: dict[str, dict[str, Any]] = {
    "manual_trigger": {
        "type": "n8n-nodes-base.manualTrigger",
        "required_parameters": [],
        "optional_parameters": [],
        "defaults": {},
        "description": "Starts workflow manually from UI or API test runs.",
    },
    "webhook_trigger": {
        "type": "n8n-nodes-base.webhook",
        "required_parameters": ["path", "httpMethod"],
        "optional_parameters": ["responseMode", "options"],
        "defaults": {"httpMethod": "POST", "responseMode": "responseNode"},
        "description": "Receives inbound HTTP requests and triggers workflow.",
    },
    "cron_trigger": {
        "type": "n8n-nodes-base.scheduleTrigger",
        "required_parameters": [],
        "optional_parameters": ["rule"],
        "defaults": {"rule": {"interval": [{"triggerAtHour": 9}]}},
        "description": "Runs on schedule using cron-like rules.",
    },
    "http_request": {
        "type": "n8n-nodes-base.httpRequest",
        "required_parameters": ["url"],
        "optional_parameters": ["method", "sendBody", "jsonBody"],
        "defaults": {"method": "GET"},
        "description": "Makes external HTTP calls.",
    },
    "set": {
        "type": "n8n-nodes-base.set",
        "required_parameters": [],
        "optional_parameters": ["values", "keepOnlySet"],
        "defaults": {"keepOnlySet": False},
        "description": "Create or modify fields in item data.",
    },
    "code": {
        "type": "n8n-nodes-base.code",
        "required_parameters": ["jsCode"],
        "optional_parameters": ["mode"],
        "defaults": {"mode": "runOnceForAllItems", "jsCode": "return items;"},
        "description": "Run JavaScript for custom transformations.",
    },
    "if": {
        "type": "n8n-nodes-base.if",
        "required_parameters": ["conditions"],
        "optional_parameters": [],
        "defaults": {},
        "description": "Route execution by condition.",
    },
    "switch": {
        "type": "n8n-nodes-base.switch",
        "required_parameters": ["rules"],
        "optional_parameters": [],
        "defaults": {},
        "description": "Route data to multiple branches.",
    },
    "merge": {
        "type": "n8n-nodes-base.merge",
        "required_parameters": [],
        "optional_parameters": ["mode"],
        "defaults": {"mode": "append"},
        "description": "Merge multiple streams into one.",
    },
    "gmail": {
        "type": "n8n-nodes-base.gmail",
        "required_parameters": ["resource", "operation"],
        "optional_parameters": ["messageId", "subject", "toEmail"],
        "defaults": {"resource": "message", "operation": "send"},
        "description": "Send or read Gmail messages.",
    },
    "slack": {
        "type": "n8n-nodes-base.slack",
        "required_parameters": ["resource", "operation"],
        "optional_parameters": ["channel", "text"],
        "defaults": {"resource": "message", "operation": "post"},
        "description": "Send Slack messages or perform Slack actions.",
    },
    "google_sheets": {
        "type": "n8n-nodes-base.googleSheets",
        "required_parameters": ["operation", "documentId"],
        "optional_parameters": ["sheetName", "range", "columns"],
        "defaults": {"operation": "append"},
        "description": "Read from and write to Google Sheets.",
    },
    "postgres": {
        "type": "n8n-nodes-base.postgres",
        "required_parameters": ["operation"],
        "optional_parameters": ["query"],
        "defaults": {"operation": "executeQuery"},
        "description": "Run queries against PostgreSQL.",
    },
    "mysql": {
        "type": "n8n-nodes-base.mySql",
        "required_parameters": ["operation"],
        "optional_parameters": ["query"],
        "defaults": {"operation": "executeQuery"},
        "description": "Run queries against MySQL.",
    },
    "mongodb": {
        "type": "n8n-nodes-base.mongoDb",
        "required_parameters": ["operation"],
        "optional_parameters": ["collection", "fields"],
        "defaults": {"operation": "find"},
        "description": "Read and write MongoDB documents.",
    },
    "discord": {
        "type": "n8n-nodes-base.discord",
        "required_parameters": ["resource", "operation"],
        "optional_parameters": ["channelId", "content"],
        "defaults": {"resource": "message", "operation": "send"},
        "description": "Send messages to Discord channels.",
    },
    "telegram": {
        "type": "n8n-nodes-base.telegram",
        "required_parameters": ["operation"],
        "optional_parameters": ["chatId", "text"],
        "defaults": {"operation": "sendMessage"},
        "description": "Send or receive Telegram messages.",
    },
    "openai": {
        "type": "@n8n/n8n-nodes-langchain.openAi",
        "required_parameters": ["operation"],
        "optional_parameters": ["model", "prompt"],
        "defaults": {"operation": "text"},
        "description": "Generate text/summaries with OpenAI.",
    },
    "respond_to_webhook": {
        "type": "n8n-nodes-base.respondToWebhook",
        "required_parameters": [],
        "optional_parameters": ["responseBody", "responseCode"],
        "defaults": {"responseCode": 200},
        "description": "Sends HTTP response for webhook workflows.",
    },
    "noop": {
        "type": "n8n-nodes-base.noOp",
        "required_parameters": [],
        "optional_parameters": [],
        "defaults": {},
        "description": "No-operation placeholder node.",
    },
    "wait": {
        "type": "n8n-nodes-base.wait",
        "required_parameters": ["amount", "unit"],
        "optional_parameters": [],
        "defaults": {"amount": 1, "unit": "minutes"},
        "description": "Pause workflow execution.",
    },
    "split_in_batches": {
        "type": "n8n-nodes-base.splitInBatches",
        "required_parameters": ["batchSize"],
        "optional_parameters": [],
        "defaults": {"batchSize": 10},
        "description": "Process items in chunks.",
    },
    "error_trigger": {
        "type": "n8n-nodes-base.errorTrigger",
        "required_parameters": [],
        "optional_parameters": [],
        "defaults": {},
        "description": "Triggers on workflow errors.",
    },
}


def registry_for_prompt() -> str:
    """Return human-readable node registry string for system prompt context."""

    lines: list[str] = []
    for key, value in NODE_REGISTRY.items():
        lines.append(
            f"- {key}: {value['type']} | required={value['required_parameters']} | "
            f"optional={value['optional_parameters']} | {value['description']}"
        )
    return "\n".join(lines)


def type_to_registry_key(node_type: str) -> str | None:
    """Return registry key for an n8n node type string."""

    for key, config in NODE_REGISTRY.items():
        if config["type"] == node_type:
            return key
    return None
