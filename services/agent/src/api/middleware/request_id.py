"""Request ID middleware for request tracing."""

from __future__ import annotations

import uuid
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID header to all requests for tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Attach to request state for use in logging
        request.state.request_id = request_id
        response = cast(Response, await call_next(request))
        response.headers["X-Request-ID"] = request_id
        return response
