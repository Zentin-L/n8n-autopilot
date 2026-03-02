"""Pydantic models for n8n workflows and related API objects."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class N8NNodeParameters(BaseModel):
    """Generic container for node parameters."""

    model_config = ConfigDict(extra="allow", strict=True)


class N8NNode(BaseModel):
    """n8n node definition."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    name: str
    type: str
    typeVersion: float
    position: list[int] = Field(min_length=2, max_length=2)
    parameters: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] | None = None


class N8NConnection(BaseModel):
    """Connection target descriptor."""

    model_config = ConfigDict(extra="forbid", strict=True)

    node: str
    type: str = "main"
    index: int = 0


class N8NWorkflow(BaseModel):
    """n8n workflow payload model."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str
    nodes: list[N8NNode]
    connections: dict[str, Any]
    active: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)
    tags: list[Any] = Field(default_factory=list)


class N8NExecution(BaseModel):
    """Execution summary model."""

    model_config = ConfigDict(extra="allow", strict=True)

    id: str | int
    workflowId: str | int | None = None
    finished: bool | None = None
    mode: str | None = None
    status: str | None = None
    startedAt: str | None = None
    stoppedAt: str | None = None
