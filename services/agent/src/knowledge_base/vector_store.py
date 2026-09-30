"""Knowledge Base - Vector store and hybrid retrieval.

Provides embedding + Milvus-based vector search with PG keyword fallback.
Supports multiple knowledge collections: viral videos, creative theory,
prompt engineering tips, cinematography terms.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.common.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 1024  # bge-m3
VISUAL_EMBEDDING_DIM = 768  # CLIP


class KnowledgeBase:
    """Unified knowledge retrieval interface.

    In MVP/offline mode: uses in-memory dictionary search (no Milvus required).
    In production: connects to Milvus for vector search.
    """

    def __init__(self, milvus_client=None, embedding_fn=None):
        self.milvus = milvus_client
        self.embed = embedding_fn or self._dummy_embed
        self._collections_initialized = False
        self._memory_store: dict[str, list[dict[str, Any]]] = {
            "creative_knowledge": [],
            "prompt_knowledge": [],
            "cinematography_knowledge": [],
            "viral_videos_text": [],
        }
        self._load_builtin_knowledge()

    def _dummy_embed(self, text: str) -> list[float]:
        """Dummy embedding for offline mode - uses hash-based pseudo-vectors."""
        import random

        rng = random.Random(hashlib.md5(text.encode()).hexdigest()[:8])
        return [rng.uniform(-1, 1) for _ in range(128)] + [0.0] * (EMBEDDING_DIM - 128)

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na * nb > 0 else 0

    def _load_builtin_knowledge(self):
        """Load built-in knowledge from JSON files into memory store."""
        data_dir = Path(__file__).parent.parent / "knowledge" / "data"
        preset_dir = Path(__file__).parent.parent / "knowledge" / "presets"
        # Load hooks
        if (data_dir / "hooks.json").exists():
            hooks = json.loads((data_dir / "hooks.json").read_text(encoding="utf-8"))
            for cat in hooks.get("categories", []):
                for tpl in cat.get("templates", []):
                    self._memory_store["creative_knowledge"].append(
                        {
                            "id": tpl["id"],
                            "knowledge_type": "hook",
                            "name": tpl["name"],
                            "category": cat["type"],
                            "content": tpl.get("template", ""),
                            "example": tpl.get("example", ""),
                            "tags": tpl.get("best_for", []),
                            "usage_count": 0,
                            "embedding": self._dummy_embed(tpl.get("template", "") + " " + tpl.get("example", "")),
                        }
                    )
        # Load story structures
        if (data_dir / "story_structures.json").exists():
            structs = json.loads((data_dir / "story_structures.json").read_text(encoding="utf-8"))
            for s in structs.get("structures", []):
                self._memory_store["creative_knowledge"].append(
                    {
                        "id": s["id"],
                        "knowledge_type": "structure",
                        "name": s["name"],
                        "category": s.get("type", "classic"),
                        "content": s.get("template", s.get("description", "")),
                        "tags": s.get("best_for", []),
                        "usage_count": 0,
                        "embedding": self._dummy_embed(s.get("name", "") + " " + s.get("description", "")),
                    }
                )
        # Load CTAs
        if (data_dir / "ctas.json").exists():
            ctas = json.loads((data_dir / "ctas.json").read_text(encoding="utf-8"))
            for c in ctas.get("strategies", []):
                self._memory_store["creative_knowledge"].append(
                    {
                        "id": c["id"],
                        "knowledge_type": "cta",
                        "name": c["name"],
                        "category": c.get("type", "action"),
                        "content": c.get("template", ""),
                        "example": c.get("example", ""),
                        "tags": c.get("best_for", []),
                        "usage_count": 0,
                        "embedding": self._dummy_embed(c.get("template", "")),
                    }
                )
        # Load emotion curves
        if (data_dir / "emotion_curves.json").exists():
            curves = json.loads((data_dir / "emotion_curves.json").read_text(encoding="utf-8"))
            for c in curves.get("curves", []):
                self._memory_store["creative_knowledge"].append(
                    {
                        "id": c["id"],
                        "knowledge_type": "emotion_curve",
                        "name": c["name"],
                        "content": c.get("description", ""),
                        "tags": c.get("best_for", []),
                        "usage_count": 0,
                        "embedding": self._dummy_embed(c.get("name", "") + " " + c.get("description", "")),
                    }
                )
        # Load style presets as prompt knowledge
        if (preset_dir / "style_presets.json").exists():
            styles = json.loads((preset_dir / "style_presets.json").read_text(encoding="utf-8"))
            for s in styles.get("presets", []):
                self._memory_store["prompt_knowledge"].append(
                    {
                        "id": s["id"],
                        "knowledge_type": "style",
                        "model_id": "",
                        "category": s.get("category", "visual_style"),
                        "title": s["name"],
                        "content": s.get("positive_fragment", ""),
                        "tags": [],
                        "embedding": self._dummy_embed(s["name"] + " " + s.get("positive_fragment", "")),
                    }
                )
        # Load cinematography terms from generator config
        from src.prompt_engine.generator import CONFIG

        for sz_key, sz in CONFIG["shot_sizes"].items():
            self._memory_store["cinematography_knowledge"].append(
                {
                    "id": f"shot_{sz_key}",
                    "category": "shot_type",
                    "term_cn": sz["cn"],
                    "term_en": sz["en"],
                    "definition": sz["cn"] + " shot size",
                    "prompt_fragment_cn": sz["cn"],
                    "prompt_fragment_en": sz["en"],
                    "tags": ["shot_size", "镜头"],
                    "embedding": self._dummy_embed(sz["cn"] + " " + sz["en"]),
                }
            )
        for mov_key, mov in CONFIG["camera_movements"].items():
            self._memory_store["cinematography_knowledge"].append(
                {
                    "id": f"mov_{mov_key}",
                    "category": "camera_movement",
                    "term_cn": mov["cn"],
                    "term_en": mov["en"],
                    "prompt_fragment_cn": mov["cn"],
                    "prompt_fragment_en": mov["en"],
                    "tags": ["movement", "运镜"],
                    "embedding": self._dummy_embed(mov["cn"] + " " + mov["en"]),
                }
            )
        for lt_key, lt in CONFIG["lighting_types"].items():
            self._memory_store["cinematography_knowledge"].append(
                {
                    "id": f"light_{lt_key}",
                    "category": "lighting",
                    "term_cn": lt["cn"],
                    "term_en": lt["en"],
                    "prompt_fragment_cn": lt["cn"],
                    "prompt_fragment_en": lt["en"],
                    "tags": ["lighting", "光线"],
                    "embedding": self._dummy_embed(lt["cn"] + " " + lt["en"]),
                }
            )
        logger.info(f"Knowledge base loaded: {sum(len(v) for v in self._memory_store.values())} entries")

    def search(self, collection: str, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict[str, Any]]:
        """Search knowledge base with vector similarity (MVP: in-memory)."""
        if collection not in self._memory_store:
            return []
        q_vec = self._dummy_embed(query)
        scored = []
        for item in self._memory_store[collection]:
            score = self._cosine_sim(q_vec, item.get("embedding", []))
            # Apply filters
            if filters:
                match = True
                for k, v in filters.items():
                    if k in item and item[k] != v:
                        match = False
                        break
                if not match:
                    continue
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored[:top_k]:
            r = {k: v for k, v in item.items() if k != "embedding"}
            r["score"] = round(score, 4)
            results.append(r)
        return results

    def add_entry(self, collection: str, entry: dict[str, Any]) -> str:
        """Add a new knowledge entry."""
        if collection not in self._memory_store:
            self._memory_store[collection] = []
        entry_id = entry.get("id") or str(uuid4())[:8]
        entry["id"] = entry_id
        text = entry.get("content", "") + " " + entry.get("name", entry.get("title", ""))
        entry["embedding"] = self._dummy_embed(text)
        entry["usage_count"] = 0
        self._memory_store[collection].append(entry)
        return entry_id

    def get_stats(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._memory_store.items()}


_singleton: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _singleton
    if _singleton is None:
        _singleton = KnowledgeBase()
    return _singleton
