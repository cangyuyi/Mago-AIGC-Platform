"""Initialize Milvus collections for Mago Knowledge Base.

Run this after Milvus is started via docker compose::

    python scripts/init_milvus.py

The script is intentionally independent of the caller's current directory.
Use ``MILVUS_HOST`` and ``MILVUS_PORT`` to connect to a non-local Milvus
instance (for example, ``milvus`` from inside the Compose network).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the Agent package importable when this script is run from any directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "services" / "agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

COLLECTIONS = {
    "creative_knowledge": {
        "description": "创意理论知识（钩子/结构/CTA/情绪曲线/节奏）",
        "embedding_dim": 1024,
    },
    "prompt_knowledge": {
        "description": "提示词工程知识（术语/技巧/Best Practice/模型提示）",
        "embedding_dim": 1024,
    },
    "cinematography_knowledge": {
        "description": "镜头语言/摄影/电影术语知识库",
        "embedding_dim": 1024,
    },
    "viral_videos_text": {
        "description": "爆款视频文本向量（02板块写入）",
        "embedding_dim": 1024,
    },
    "viral_videos_visual": {
        "description": "爆款视频关键帧CLIP视觉向量（02板块写入）",
        "embedding_dim": 768,
    },
}


def _milvus_endpoint() -> tuple[str, int]:
    host = os.getenv("MILVUS_HOST", "localhost").strip() or "localhost"
    raw_port = os.getenv("MILVUS_PORT", "19530").strip() or "19530"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"MILVUS_PORT must be an integer, got {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"MILVUS_PORT must be between 1 and 65535, got {port}")
    return host, port


def main() -> int:
    try:
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    except ImportError:
        print("⚠️  pymilvus not installed. Run: pip install pymilvus")
        print("In offline mode, the in-memory knowledge base is used automatically.")
        return 0

    host, port = _milvus_endpoint()
    print(f"Connecting to Milvus at {host}:{port}...")
    connections.connect("default", host=host, port=port)

    try:
        for name, config in COLLECTIONS.items():
            if utility.has_collection(name):
                print(f"  ✅ {name} already exists")
                continue
            dim = config["embedding_dim"]
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
                FieldSchema(name="knowledge_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(
                    name="tags",
                    dtype=DataType.ARRAY,
                    element_type=DataType.VARCHAR,
                    max_length=64,
                    max_capacity=30,
                ),
                FieldSchema(name="created_at", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            schema = CollectionSchema(fields, description=config["description"])
            collection = Collection(name, schema)
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            print(f"  ✅ Created {name} (dim={dim})")
    finally:
        connections.disconnect("default")

    print("\n✅ All Milvus collections initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
