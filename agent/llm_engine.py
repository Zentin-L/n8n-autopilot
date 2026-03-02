"""LLM integration for intent understanding and tool-calling."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from openai import OpenAI

from config import get_settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ToolCall:
    """Represents a single LLM tool invocation."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class AgentResponse:
    """Normalized LLM response object."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMEngine:
    """Wraps OpenAI chat completions with memory and tool-calling support."""

    def __init__(self, system_prompt: str) -> None:
        settings = get_settings()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    def clear_memory(self) -> None:
        """Clear conversation memory while preserving system prompt."""

        self.messages = [self.messages[0]]

    def process_message(
        self,
        user_input: str,
        tools: list[dict[str, Any]],
        *,
        stream: bool = False,
    ) -> AgentResponse | Iterable[str]:
        """Process user input and optionally stream output tokens."""

        self.messages.append({"role": "user", "content": user_input})

        if stream:
            return self._stream_text(tools)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )

        message = response.choices[0].message
        tool_calls = self._parse_tool_calls(message.tool_calls)
        content = message.content or ""
        self.messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in tool_calls
                ]
                if tool_calls
                else None,
            }
        )
        return AgentResponse(content=content, tool_calls=tool_calls)

    def submit_tool_results(
        self,
        tool_outputs: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AgentResponse:
        """Submit tool outputs and obtain next LLM response."""

        for item in tool_outputs:
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item["tool_call_id"],
                    "content": json.dumps(item["output"]),
                }
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )
        message = response.choices[0].message
        tool_calls = self._parse_tool_calls(message.tool_calls)
        content = message.content or ""
        self.messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in tool_calls
                ]
                if tool_calls
                else None,
            }
        )
        return AgentResponse(content=content, tool_calls=tool_calls)

    def _stream_text(self, tools: list[dict[str, Any]]) -> Iterable[str]:
        """Stream plain assistant tokens (without tool loop)."""

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools,
            tool_choice="none",
            stream=True,
            temperature=0.2,
        )

        chunks: list[str] = []
        for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta
            if delta and delta.content:
                chunks.append(delta.content)
                yield delta.content

        self.messages.append({"role": "assistant", "content": "".join(chunks)})

    @staticmethod
    def _parse_tool_calls(raw_tool_calls: Any) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        if not raw_tool_calls:
            return tool_calls

        for call in raw_tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                logger.warning("Failed to parse tool arguments for %s", call.function.name)
                arguments = {}
            tool_calls.append(
                ToolCall(id=call.id, name=call.function.name, arguments=arguments)
            )
        return tool_calls
