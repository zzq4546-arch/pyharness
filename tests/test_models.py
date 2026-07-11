from dataclasses import asdict
from pyharness.models import (
    Message, Action, GuardResult, ToolResult, Feedback, MemoryEntry, AgentState
)


def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_call_id is None
    assert msg.tool_result is None


def test_message_with_tool():
    msg = Message(role="tool", content="", tool_call_id="call_1", tool_result="done")
    assert msg.tool_call_id == "call_1"
    assert msg.tool_result == "done"


def test_action_tool_call():
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "print(1)"},
                    thought="creating file")
    assert action.type == "tool_call"
    assert action.tool_name == "write_file"
    assert action.tool_args["path"] == "a.py"
    assert action.stop_reason is None


def test_action_stop():
    action = Action(type="stop", stop_reason="task_complete",
                    thought="done")
    assert action.type == "stop"
    assert action.stop_reason == "task_complete"


def test_guard_result_blocked():
    gr = GuardResult(blocked=True, needs_approval=False,
                     reason="dangerous command", guard_name="RuleGuard")
    assert gr.blocked is True
    assert gr.guard_name == "RuleGuard"


def test_guard_result_approval():
    gr = GuardResult(blocked=False, needs_approval=True,
                     reason="network request", guard_name="ApprovalGuard")
    assert gr.needs_approval is True


def test_tool_result_success():
    tr = ToolResult(tool_name="read_file", success=True,
                    output="file content", error=None, exit_code=0)
    assert tr.success is True
    assert tr.output == "file content"


def test_tool_result_failure():
    tr = ToolResult(tool_name="execute_shell", success=False,
                    output="", error="command not found", exit_code=127)
    assert tr.success is False
    assert tr.exit_code == 127


def test_feedback_pass():
    fb = Feedback(status="PASS", summary="all tests passed",
                  details=[], round=3)
    assert fb.status == "PASS"
    assert fb.round == 3


def test_feedback_fail():
    fb = Feedback(status="FAIL", summary="3 tests failed",
                  details=[{"test": "test_add", "error": "AssertionError"}],
                  round=2)
    assert fb.status == "FAIL"
    assert len(fb.details) == 1


def test_memory_entry():
    entry = MemoryEntry(id="mem_1", category="convention",
                        content="use pytest for testing",
                        keywords=["test", "pytest"])
    assert entry.category == "convention"
    assert "pytest" in entry.keywords
    assert entry.created_at is not None
    assert entry.updated_at is not None


def test_agent_state():
    state = AgentState(status="IDLE", current_round=0, max_rounds=10,
                       tokens_used=0, guardrail_blocks=0,
                       pending_approval=None)
    assert state.status == "IDLE"
    assert state.current_round == 0
    assert state.pending_approval is None