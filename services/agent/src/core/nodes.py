"""Node interface and registry for LangGraph nodes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

# A node is an async function: (state, deps) -> state_update
NodeFunction = Callable[..., Awaitable[dict[str, Any]]]


class NodeRegistry:
    """Registry of all available agent nodes."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeFunction] = {}

    def register(self, name: str, func: NodeFunction) -> None:
        self._nodes[name] = func

    def get(self, name: str) -> NodeFunction:
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not registered. Available: {list(self._nodes.keys())}")
        return self._nodes[name]

    def list_nodes(self) -> list[str]:
        return list(self._nodes.keys())


# Global registry
registry = NodeRegistry()
