import json
import os
import tempfile
import threading
from pyharness.loop import AgentLoop
from pyharness.config import ConfigLoader
from pyharness.llm import MockProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine


def build_harness(workspace, llm_responses, max_rounds=10):
    config = ConfigLoader()
    config.load()
    config._config["max_rounds"] = max_rounds
    config._config["tools"]["enabled"] = ["read_file", "write_file", "execute_shell",
                                           "run_tests", "run_lint", "list_files"]
    llm = MockProvider(responses=llm_responses)
    parser = ActionParser()
    guardrail = GuardrailChain([
        RuleGuard(config),
        ScopeGuard(config, workspace),
        ApprovalGuard(config),
    ])
    tools = ToolExecutor(config, workspace=workspace)
    feedback = FeedbackCollector(config)
    memory = MemoryStore(os.path.join(workspace, ".harness", "memory"))
    context = ContextManager(config, memory, workspace=workspace)
    hitl = HITLEngine(timeout=30)
    loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, workspace)
    return loop, hitl


def test_demo_1_guardrail_blocks_dangerous_action():
    """演示 1: 治理护栏拦截危险动作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loop, hitl = build_harness(tmpdir, llm_responses=[
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "rm -rf /"}, "thought": "cleaning up"}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        events = []
        result = loop.run("delete everything", on_event=events.append)

        guard_events = [e for e in events if e.get("type") == "guardrail"]
        assert len(guard_events) > 0
        assert guard_events[0]["result"]["blocked"] is True
        assert guard_events[0]["result"]["guard_name"] == "RuleGuard"


def test_demo_2_feedback_loop_changes_behavior():
    """演示 2: 注入失败，反馈闭环使 agent 收到反馈并改变下一步动作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_calc.py")
        with open(test_file, "w") as f:
            f.write("def test_add():\n    assert 1 + 1 == 3\n")

        loop, hitl = build_harness(tmpdir, llm_responses=[
            json.dumps({"type": "tool_call", "tool_name": "run_tests", "tool_args": {"command": "pytest test_calc.py"}, "thought": "running tests"}),
            json.dumps({"type": "tool_call", "tool_name": "write_file", "tool_args": {"path": test_file, "content": "def test_add():\n    assert 1 + 1 == 2\n"}, "thought": "fixing the test based on feedback"}),
            json.dumps({"type": "tool_call", "tool_name": "run_tests", "tool_args": {"command": "pytest test_calc.py"}, "thought": "re-running tests after fix"}),
            json.dumps({"type": "stop", "stop_reason": "task_complete", "thought": "tests pass now"}),
        ])
        events = []
        result = loop.run("fix the failing test", on_event=events.append)

        feedback_events = [e for e in events if e.get("type") == "feedback"]
        assert len(feedback_events) >= 3

        first_feedback = feedback_events[0]
        assert first_feedback["status"] == "ERROR"

        write_feedback = feedback_events[1]
        assert write_feedback["status"] == "PASS"

        actions = [e for e in events if e.get("type") == "action"]
        assert any("write_file" in str(e.get("tool_name", "")) for e in actions)
        assert any("fix" in str(e.get("thought", "")).lower() for e in actions)


def test_demo_3_hitl_approval_with_timeout_reject():
    """演示 3: HITL 审批超时默认拒绝（重点维度：护栏）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loop, hitl = build_harness(tmpdir, llm_responses=[
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "pip install requests"}, "thought": "installing dependency"}',
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "pytest"}, "thought": "running tests without the dependency"}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        events = []
        result = loop.run("install requests", on_event=events.append)

        approval_events = [e for e in events if e.get("type") == "approval_required"]
        assert len(approval_events) > 0
        assert approval_events[0]["action"]["tool_name"] == "execute_shell"

        timeouts = [e for e in events if e.get("type") == "approval_result" and e.get("decision") == "timeout"]
        assert len(timeouts) > 0