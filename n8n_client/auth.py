"""Authentication helpers for n8n API requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class N8NAuth:
    """Authentication settings container."""

    api_key: str

    def headers(self) -> dict[str, str]:
        """Return authentication headers for n8n API."""

        return {"X-N8N-API-KEY": self.api_key} if self.api_key else {}
