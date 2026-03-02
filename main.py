"""Interactive CLI entrypoint for the n8n AI agent."""

from __future__ import annotations

import logging
import os
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from agent.core import AgentTurnResult, N8NAgent
from config import get_settings


console = Console()


def configure_logging() -> None:
    """Configure root logger from environment."""

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def print_welcome() -> None:
    """Show startup information and commands."""

    console.print(
        Panel.fit(
            "\n".join(
                [
                    "n8n AI Agent",
                    "Natural-language workflow creation and management over n8n REST API.",
                    "Commands: /help, /workflows, /clear, /quit",
                ]
            ),
            title="Welcome",
        )
    )


def render_workflows(workflows: list[dict[str, Any]]) -> None:
    """Render workflows in a formatted table."""

    table = Table(title="Workflows")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Active")
    table.add_column("Updated")

    for workflow in workflows:
        table.add_row(
            str(workflow.get("id", "")),
            str(workflow.get("name", "")),
            str(workflow.get("active", "")),
            str(workflow.get("updatedAt", "")),
        )
    console.print(table)


def render_executions(executions: list[dict[str, Any]]) -> None:
    """Render executions in formatted table."""

    table = Table(title="Execution History")
    table.add_column("ID")
    table.add_column("Workflow ID")
    table.add_column("Status")
    table.add_column("Started")
    table.add_column("Stopped")
    for execution in executions:
        table.add_row(
            str(execution.get("id", "")),
            str(execution.get("workflowId", "")),
            str(execution.get("status", execution.get("finished", ""))),
            str(execution.get("startedAt", "")),
            str(execution.get("stoppedAt", "")),
        )
    console.print(table)


def handle_result(agent: N8NAgent, result: AgentTurnResult) -> None:
    """Display agent results and handle confirmation workflows."""

    if result.preview_workflow:
        console.print(Panel.fit("Workflow JSON preview", title="Preview"))
        console.print_json(data=result.preview_workflow)

    if result.pending_action:
        action = result.pending_action.action
        message = f"Confirm action: {action}?"
        if Confirm.ask(message, default=False):
            confirmation_result = agent.confirm_pending_action()
            console.print(Panel.fit("Action executed", title="Confirmation"))
            console.print_json(data=confirmation_result)
        else:
            console.print("Action cancelled.")
            agent.pending_action = None

    if result.tool_results:
        for item in result.tool_results:
            output = item.get("output", {})
            if "workflows" in output and isinstance(output["workflows"], list):
                render_workflows(output["workflows"])
            if "executions" in output and isinstance(output["executions"], list):
                render_executions(output["executions"])

    if result.text:
        console.print(result.text)


def main() -> None:
    """Run interactive CLI loop."""

    configure_logging()
    print_welcome()
    agent = N8NAgent()

    try:
        while True:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
            if not user_input:
                continue

            if user_input in {"/quit", "/exit"}:
                console.print("Goodbye.")
                break
            if user_input == "/help":
                console.print(
                    "Commands: /help, /workflows, /clear, /quit\n"
                    "Examples:\n"
                    "- Create a workflow that runs daily and sends Slack message\n"
                    "- List all my workflows\n"
                    "- Execute workflow ID 5"
                )
                continue
            if user_input == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_welcome()
                continue
            if user_input == "/workflows":
                workflows = agent.client.list_workflows()
                render_workflows(workflows)
                continue

            try:
                result = agent.handle_message(user_input)
                handle_result(agent, result)
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
