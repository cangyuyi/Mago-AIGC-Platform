"""Small authorization helpers shared by Agent HTTP routes."""

from __future__ import annotations

from fastapi import HTTPException, Request


def require_roles(request: Request, *roles: str) -> None:
    """Require one of ``roles`` when Agent authentication is enabled.

    Development mode intentionally keeps the service convenient to run without
    JWTs. Production deployments enable the middleware in ``main.py``; in that
    mode the middleware has already populated ``request.state.user_role``.
    """
    from src.config import get_settings

    if not get_settings().agent_auth_enabled:
        return
    role = getattr(request.state, "user_role", None)
    if role not in roles:
        raise HTTPException(status_code=403, detail="insufficient permissions")
