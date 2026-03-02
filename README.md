# n8n AI Agent

Python AI agent application that connects to n8n via REST API and creates, manages, and executes workflows from natural language.

## Features

- Natural language to n8n workflow generation
- Workflow CRUD, activation/deactivation, and manual execution
- Execution history lookup
- Tool-calling agent loop with Hugging Face
- Workflow JSON preview and confirmation before creation
- Confirmation before destructive deletion
- Rich CLI interface with built-in commands

## Project Structure

```
n8n-ai-agent/
├── main.py
├── agent/
│   ├── __init__.py
│   ├── core.py
│   ├── llm_engine.py
│   ├── workflow_builder.py
│   ├── node_registry.py
│   └── prompt_templates.py
├── n8n_client/
│   ├── __init__.py
│   ├── api_client.py
│   ├── models.py
│   └── auth.py
├── tools/
│   ├── __init__.py
│   ├── create_workflow.py
│   ├── update_workflow.py
│   ├── delete_workflow.py
│   ├── list_workflows.py
│   ├── execute_workflow.py
│   ├── get_executions.py
│   └── add_node.py
├── config.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy environment template and fill keys:

   ```bash
   copy .env.example .env
   ```

   Required:
   - `N8N_BASE_URL`
   - `N8N_API_KEY`
   - `HUGGINGFACE_API_KEY`
   - `HUGGINGFACE_BASE_URL`
   - `HUGGINGFACE_MODEL`

3. Run the CLI:

   ```bash
   python main.py
   ```

## CLI Commands

- `/help` – usage and examples
- `/workflows` – list workflows directly
- `/clear` – clear screen
- `/quit` – exit

## Example Prompts

- Create a workflow that triggers every morning at 9am and sends a Slack message saying Good Morning to #general.
- Build a workflow with a webhook trigger that receives JSON data, filters items where status is active, then saves them to a Google Sheet.
- Create a workflow that monitors Gmail inbox attachments, summarizes via Llama 3.3, and posts to Discord.
- List all my workflows.
- Execute workflow ID 5.
- Deactivate all workflows with test in the name.

## Notes

- n8n node types and defaults are defined in `agent/node_registry.py`.
- Workflow JSON construction and connection mapping are implemented in `agent/workflow_builder.py`.
- API retries with exponential backoff and timeout handling are in `n8n_client/api_client.py`.
