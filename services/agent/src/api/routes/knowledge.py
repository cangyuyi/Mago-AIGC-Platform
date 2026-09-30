"""Knowledge base search and management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from src.api.auth import require_roles
from src.knowledge_base.vector_store import get_knowledge_base

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class KnowledgeEntry(BaseModel):
    collection: str
    entry: dict[str, Any]


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    collection: str = Query("creative_knowledge", description="Collection to search"),
    top_k: int = Query(5, ge=1, le=20),
):
    kb = get_knowledge_base()
    results = kb.search(collection, q, top_k=top_k)
    return {"query": q, "collection": collection, "results": results, "count": len(results)}


@router.get("/collections")
async def list_collections():
    kb = get_knowledge_base()
    return {"collections": list(kb._memory_store.keys()), "stats": kb.get_stats()}


@router.post("/entries")
async def add_entry(req: KnowledgeEntry, request: Request):
    require_roles(request, "owner", "admin")
    kb = get_knowledge_base()
    entry_id = kb.add_entry(req.collection, req.entry)
    return {"id": entry_id, "collection": req.collection}


@router.get("/stats")
async def knowledge_stats():
    kb = get_knowledge_base()
    return kb.get_stats()
