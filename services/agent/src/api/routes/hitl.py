"""Human-in-the-Loop endpoints: natural language modification, feedback."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.agents.hitl.nl_modify import NLModifyAgent
from src.agents.hitl.version_manager import get_version_manager

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


def _owner_id(request: Request) -> str:
    """Return the verified owner, retaining anonymous local-mode behavior."""
    return str(getattr(request.state, "user_id", None) or "anonymous")


class ModifyRequest(BaseModel):
    feedback: str = Field(..., description="User's natural language modification request")
    script: dict[str, Any] | None = None
    storyboard: dict[str, Any] | None = None
    apply: bool = Field(default=False, description="Whether to apply modifications immediately")


class VersionSaveRequest(BaseModel):
    entity_id: str
    data: dict[str, Any]
    note: str = ""
    author: str = "user"


@router.post("/modify")
async def modify_script(req: ModifyRequest):
    agent = NLModifyAgent()
    result = await agent.modify(req.feedback, req.script, req.storyboard)
    response = {
        "modifications": result.get("modifications", []),
        "explanation": result.get("explanation", ""),
        "requires_regeneration": result.get("requires_regeneration", False),
    }
    if req.apply and req.script:
        modified_script = agent.apply_modifications_to_script(req.script, result["modifications"])
        response["modified_script"] = modified_script
    if req.apply and req.storyboard:
        modified_sb = agent.apply_modifications_to_storyboard(req.storyboard, result["modifications"])
        response["modified_storyboard"] = modified_sb
    return response


@router.post("/versions")
async def save_version(req: VersionSaveRequest, request: Request):
    vm = get_version_manager()
    owner_id = _owner_id(request)
    author = owner_id if owner_id != "anonymous" else req.author
    vid = vm.save_version(req.entity_id, req.data, req.note, author, owner_id)
    return {"version_id": vid}


@router.get("/versions/{entity_id}")
async def list_versions(entity_id: str, request: Request):
    vm = get_version_manager()
    return {"versions": vm.list_versions(entity_id, _owner_id(request))}


@router.get("/versions/{entity_id}/diff")
async def diff_versions(entity_id: str, v1: str, v2: str, request: Request):
    vm = get_version_manager()
    return vm.diff(entity_id, v1, v2, _owner_id(request))


@router.post("/versions/{entity_id}/rollback")
async def rollback(entity_id: str, version: str, request: Request):
    vm = get_version_manager()
    data = vm.rollback(entity_id, version, _owner_id(request))
    if data is None:
        return {"error": "version not found"}
    return {"data": data}
