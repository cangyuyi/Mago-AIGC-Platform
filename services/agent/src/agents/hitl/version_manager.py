"""Version Manager - tracks script/storyboard versions with diff support."""

from __future__ import annotations

import copy
import difflib
from datetime import datetime
from typing import Any, cast


class VersionManager:
    """Manages version history for scripts and storyboards with diff generation."""

    def __init__(self):
        # Include the authenticated owner in the storage key. The manager is
        # process-local today, but it must still enforce tenant isolation while
        # it is used by a multi-user API process.
        self._versions: dict[str, list[dict[str, Any]]] = {}

    @staticmethod
    def _key(entity_id: str, owner_id: str | None = None) -> str:
        return f"{owner_id or 'anonymous'}:{entity_id}"

    def save_version(
        self,
        entity_id: str,
        data: dict[str, Any],
        note: str = "",
        author: str = "agent",
        owner_id: str | None = None,
    ) -> str:
        key = self._key(entity_id, owner_id)
        vid = f"v{len(self._versions.get(key, [])) + 1}"
        version = {
            "version_id": vid,
            "timestamp": datetime.now().isoformat(),
            "author": author,
            "note": note,
            "data": copy.deepcopy(data),
        }
        if key not in self._versions:
            self._versions[key] = []
        self._versions[key].append(version)
        return vid

    def get_version(self, entity_id: str, version_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        for v in self._versions.get(self._key(entity_id, owner_id), []):
            if v["version_id"] == version_id:
                return v
        return None

    def list_versions(self, entity_id: str, owner_id: str | None = None) -> list[dict[str, Any]]:
        return [
            {"version_id": v["version_id"], "timestamp": v["timestamp"], "author": v["author"], "note": v["note"]}
            for v in self._versions.get(self._key(entity_id, owner_id), [])
        ]

    def diff(self, entity_id: str, v1: str, v2: str, owner_id: str | None = None) -> dict[str, Any]:
        """Generate a textual diff between two versions."""
        ver1 = self.get_version(entity_id, v1, owner_id)
        ver2 = self.get_version(entity_id, v2, owner_id)
        if not ver1 or not ver2:
            return {"error": "version not found"}
        t1 = json_dumps_sorted(ver1["data"])
        t2 = json_dumps_sorted(ver2["data"])
        diff = difflib.unified_diff(t1.splitlines(), t2.splitlines(), lineterm="", fromfile=v1, tofile=v2)
        return {"diff": list(diff), "v1": v1, "v2": v2}

    def rollback(self, entity_id: str, version_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        v = self.get_version(entity_id, version_id, owner_id)
        if v:
            return cast(dict[str, Any], copy.deepcopy(v["data"]))
        return None


def json_dumps_sorted(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


_instance: VersionManager | None = None


def get_version_manager() -> VersionManager:
    global _instance
    if _instance is None:
        _instance = VersionManager()
    return _instance
