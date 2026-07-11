import os
import json
from datetime import datetime
from typing import Optional, List
from pyharness.models import MemoryEntry


class MemoryStore:
    def __init__(self, storage_dir: str = ".harness/memory"):
        self._storage_dir = storage_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    def add(self, entry: MemoryEntry):
        filepath = os.path.join(self._storage_dir, f"{entry.id}.json")
        data = {
            "id": entry.id,
            "category": entry.category,
            "content": entry.content,
            "keywords": entry.keywords,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_all(self) -> List[MemoryEntry]:
        entries = []
        if not os.path.exists(self._storage_dir):
            return entries
        for filename in os.listdir(self._storage_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self._storage_dir, filename)
                entry = self._load_entry(filepath)
                if entry:
                    entries.append(entry)
        return entries

    def search(self, query: str) -> List[MemoryEntry]:
        query_lower = query.lower()
        results = []
        for entry in self.list_all():
            if query_lower in entry.content.lower():
                results.append(entry)
                continue
            for kw in entry.keywords:
                if query_lower in kw.lower():
                    results.append(entry)
                    break
        return results

    def delete(self, entry_id: str):
        filepath = os.path.join(self._storage_dir, f"{entry_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def _load_entry(self, filepath: str) -> Optional[MemoryEntry]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MemoryEntry(
                id=data["id"],
                category=data["category"],
                content=data["content"],
                keywords=data.get("keywords", []),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )
        except (json.JSONDecodeError, KeyError):
            return None