import tempfile
import os
from pyharness.loop import AgentLoop
from pyharness.config import ConfigLoader
from pyharness.llm import MockProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine


def test_loop_completes_with_stop_action():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        llm = MockProvider(responses=[
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([RuleGuard(config), ScopeGuard(config, tmpdir)])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        result = loop.run("write hello world", on_event=events.append)
        assert result["status"] == "completed"
        assert result["rounds"] == 1


def test_loop_stops_on_max_rounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        config._config["max_rounds"] = 2
        llm = MockProvider(responses=[
            '{"type": "response", "thought": "thinking..."}',
            '{"type": "response", "thought": "still thinking..."}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        result = loop.run("task", on_event=events.append)
        assert result["status"] == "max_rounds"
        assert result["rounds"] == 2


def test_loop_manual_stop():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        config._config["max_rounds"] = 10
        llm = MockProvider(responses=[
            '{"type": "response", "thought": "thinking..."}',
        ] * 10)
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []

        import threading
        def stop_after_delay():
            import time
            time.sleep(0.05)
            loop.stop()

        threading.Thread(target=stop_after_delay).start()
        result = loop.run("task", on_event=events.append)
        assert result["status"] == "stopped"


def test_loop_events_include_log_messages():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        llm = MockProvider(responses=[
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        loop.run("task", on_event=events.append)
        assert len(events) > 0
        assert any("started" in str(e).lower() for e in events)
        assert any("completed" in str(e).lower() for e in events)