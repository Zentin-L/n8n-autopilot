"""Robust n8n REST API client."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from config import get_settings
from n8n_client.auth import N8NAuth


logger = logging.getLogger(__name__)


class N8NAPIError(RuntimeError):
    """Raised when n8n API returns an error response."""


class N8NClient:
    """Client for n8n REST API with retry and timeout handling."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.N8N_BASE_URL.rstrip("/")
        self.timeout = settings.REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.MAX_RETRIES
        self.retry_backoff_base = settings.RETRY_BACKOFF_BASE_SECONDS
        self.auth = N8NAuth(api_key=settings.N8N_API_KEY)
        self.client = httpx.Client(timeout=self.timeout)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self.auth.headers(),
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("n8n API call: %s %s", method.upper(), url)
                response = self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )
                if response.status_code >= 400:
                    message = self._extract_error(response)
                    raise N8NAPIError(
                        f"n8n API error {response.status_code}: {message}"
                    )

                if not response.content:
                    return {}
                return response.json()
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt >= self.max_retries:
                    raise N8NAPIError(f"Connection/timeout error: {exc}") from exc
                sleep_for = self.retry_backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Transient n8n API error (attempt %s/%s): %s. Retrying in %.2fs",
                    attempt,
                    self.max_retries,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)
            except httpx.HTTPError as exc:
                raise N8NAPIError(f"HTTP error: {exc}") from exc

        raise N8NAPIError("Unexpected API request failure")

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return str(payload.get("message") or payload)
            return str(payload)
        except Exception:
            return response.text or "Unknown error"

    def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/workflows", json_data=workflow_data)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/workflows/{workflow_id}")

    def update_workflow(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PUT", f"/api/v1/workflows/{workflow_id}", json_data=workflow_data
        )

    def delete_workflow(self, workflow_id: str) -> bool:
        self._request("DELETE", f"/api/v1/workflows/{workflow_id}")
        return True

    def list_workflows(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/v1/workflows")
        if isinstance(data, dict) and "data" in data:
            return data["data"] if isinstance(data["data"], list) else []
        return data if isinstance(data, list) else []

    def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/activate")

    def deactivate_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")

    def execute_workflow(
        self, workflow_id: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/v1/workflows/{workflow_id}/run", json_data=data or {}
        )

    def get_executions(self, workflow_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workflow_id:
            params["workflowId"] = workflow_id
        data = self._request("GET", "/api/v1/executions", params=params)
        if isinstance(data, dict) and "data" in data:
            return data["data"] if isinstance(data["data"], list) else []
        return data if isinstance(data, list) else []

    def get_credentials(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/v1/credentials")
        if isinstance(data, dict) and "data" in data:
            return data["data"] if isinstance(data["data"], list) else []
        return data if isinstance(data, list) else []

    def close(self) -> None:
        """Close underlying HTTP resources."""

        self.client.close()
