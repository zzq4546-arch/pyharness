import os
import tempfile
from pyharness.context import ContextManager
from pyharness.config import ConfigLoader
from pyharness.memory import MemoryStore
from pyharness.models import Message, Feedback, MemoryEntry


def test_build_messages_with_task():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("write a calculator", [], None)
        assert len(msgs) >= 2
        assert any(m.role == "system" for m in msgs)
        assert any(m.role == "user" and "write a calculator" in m.content for m in msgs)


def test_build_messages_with_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        history = [
            Message(role="user", content="write a test"),
            Message(role="assistant", content="ok"),
        ]
        msgs = ctx.build_messages("fix the test", history, None)
        assert len(msgs) >= 4


def test_build_messages_with_feedback():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        fb = Feedback(status="FAIL", summary="test_add failed: AssertionError",
                      details=[{"error": "assert 1 == 2"}])
        msgs = ctx.build_messages("fix the test", [], fb)
        feedback_msg = [m for m in msgs if "test_add failed" in m.content]
        assert len(feedback_msg) > 0


def test_build_messages_with_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        memory.add(MemoryEntry(id="1", category="convention",
                               content="Use pytest for all tests", keywords=["test", "pytest"]))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("write tests", [], None)
        memory_content = [m for m in msgs if "pytest" in m.content and m.role != "user"]
        assert len(memory_content) > 0


def test_system_prompt_contains_essential_parts():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("task", [], None)
        system = next(m for m in msgs if m.role == "system")
        assert "coding agent" in system.content.lower()
        assert "tool" in system.content.lower()