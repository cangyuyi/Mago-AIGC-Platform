#!/usr/bin/env python3
"""Database-backed HTTP journey for the Go API Gateway (standard library only)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any


def request(base: str, method: str, path: str, payload: dict[str, Any] | None = None,
            token: str = "") -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    decoded = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(decoded, dict):
        raise AssertionError(f"{method} {path}: expected JSON object, got {decoded!r}")
    return status, decoded


def expect(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print("  ✓ " + label, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print("Mago Go API E2E: PostgreSQL-backed auth and project ownership journey")
    status, health = request(base, "GET", "/health")
    expect(status == 200 and (health.get("data") or {}).get("status") == "ok", "Gateway health")

    status, _ = request(base, "GET", "/api/v1/projects")
    expect(status == 401, "protected project API rejects anonymous requests")

    def register(label: str) -> tuple[str, str]:
        email = f"mago-e2e-{label}-{uuid.uuid4().hex[:12]}@example.test"
        status, result = request(base, "POST", "/api/v1/auth/register", {
            "email": email, "password": "E2E-password-2026", "name": f"E2E {label.title()}"
        })
        data = result.get("data") or {}
        expect(status == 200 and bool(data.get("access_token")), f"register {label} and receive access token")
        return email, str(data["access_token"])

    email_a, token_a = register("owner")
    status, _ = request(base, "POST", "/api/v1/auth/register", {
        "email": email_a, "password": "E2E-password-2026", "name": "Duplicate E2E Owner"
    })
    expect(status == 409, "duplicate email registration is rejected")

    status, me = request(base, "GET", "/api/v1/auth/me", token=token_a)
    expect(status == 200 and (me.get("data") or {}).get("email") == email_a, "JWT authenticates /auth/me")

    status, login = request(base, "POST", "/api/v1/auth/login", {
        "email": email_a, "password": "E2E-password-2026"
    })
    token_a = str((login.get("data") or {}).get("access_token", ""))
    expect(status == 200 and bool(token_a), "registered credentials can log in")
    status, _ = request(base, "POST", "/api/v1/auth/login", {
        "email": email_a, "password": "incorrect-password"
    })
    expect(status == 401, "incorrect password is rejected")

    status, created = request(base, "POST", "/api/v1/projects", {
        "name": "E2E product video", "description": "Gateway integration test",
        "target_platform": "douyin", "target_duration": 30, "category": "review"
    }, token_a)
    project = created.get("data") or {}
    project_id = str(project.get("id", ""))
    expect(status == 200 and bool(project_id) and project.get("aspect_ratio") == "9:16",
           "authenticated user creates a project with defaults")

    status, fetched = request(base, "GET", "/api/v1/projects/" + project_id, token=token_a)
    expect(status == 200 and (fetched.get("data") or {}).get("name") == "E2E product video",
           "project can be fetched by its owner")
    status, listing = request(base, "GET", "/api/v1/projects", token=token_a)
    page = listing.get("data") or {}
    expect(status == 200 and any(str(item.get("id")) == project_id for item in page.get("items", [])),
           "owner project list contains the created project")

    status, updated = request(base, "PUT", "/api/v1/projects/" + project_id,
                              {"name": "E2E product video updated"}, token=token_a)
    expect(status == 200 and (updated.get("data") or {}).get("name") == "E2E product video updated",
           "owner can update project")

    _, token_b = register("other")
    status, _ = request(base, "GET", "/api/v1/projects/" + project_id, token=token_b)
    expect(status == 404, "another user cannot read the project (non-enumerating 404)")
    status, _ = request(base, "PUT", "/api/v1/projects/" + project_id,
                        {"name": "Unauthorized project takeover"}, token_b)
    expect(status == 404, "another user cannot update the project (non-enumerating 404)")
    status, _ = request(base, "DELETE", "/api/v1/projects/" + project_id, token=token_b)
    expect(status == 404, "another user cannot delete the project (non-enumerating 404)")
    status, still_owned = request(base, "GET", "/api/v1/projects/" + project_id, token=token_a)
    expect(status == 200 and (still_owned.get("data") or {}).get("name") == "E2E product video updated",
           "unauthorized mutations leave the owner's project unchanged")
    status, listing_b = request(base, "GET", "/api/v1/projects", token=token_b)
    page_b = listing_b.get("data") or {}
    expect(status == 200 and all(str(item.get("id")) != project_id for item in page_b.get("items", [])),
           "project is absent from another user's list")

    status, _ = request(base, "DELETE", "/api/v1/projects/" + project_id, token=token_a)
    expect(status == 200, "owner can delete project")
    status, _ = request(base, "GET", "/api/v1/projects/" + project_id, token=token_a)
    expect(status == 404, "deleted project is no longer readable")
    print("E2E passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"E2E failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
