import os
import tempfile
from pyharness.memory import MemoryStore
from pyharness.models import MemoryEntry


def test_memory_add_and_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        entry = MemoryEntry(id="mem_1", category="convention",
                            content="Use pytest for all tests",
                            keywords=["test", "pytest"])
        store.add(entry)
        entries = store.list_all()
        assert len(entries) == 1
        assert entries[0].content == "Use pytest for all tests"


def test_memory_search_by_keyword():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="Use pytest", keywords=["test"]))
        store.add(MemoryEntry(id="2", category="decision",
                              content="Use FastAPI", keywords=["web"]))
        results = store.search("pytest")
        assert len(results) == 1
        assert results[0].id == "1"


def test_memory_search_by_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="Always use type hints", keywords=["typing"]))
        results = store.search("type hints")
        assert len(results) == 1


def test_memory_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="test", keywords=[]))
        store.delete("1")
        assert len(store.list_all()) == 0


def test_memory_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem_dir = os.path.join(tmpdir, "memory")
        store1 = MemoryStore(storage_dir=mem_dir)
        store1.add(MemoryEntry(id="1", category="preference",
                               content="Prefer black formatting", keywords=["format"]))
        store2 = MemoryStore(storage_dir=mem_dir)
        entries = store2.list_all()
        assert len(entries) == 1
        assert entries[0].content == "Prefer black formatting"