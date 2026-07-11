import time
import threading
from pyharness.hitl import HITLEngine
from pyharness.models import Action


def test_hitl_approve_flow():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pip install x"}, thought="")
    aid = engine.request_approval(action)

    def approve():
        engine.approve(aid)
    threading.Thread(target=approve).start()

    result = engine.wait_for_decision(aid)
    assert result == "approved"


def test_hitl_reject_flow():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)

    def reject():
        engine.reject(aid)
    threading.Thread(target=reject).start()

    result = engine.wait_for_decision(aid)
    assert result == "rejected"


def test_hitl_timeout_defaults_to_reject():
    engine = HITLEngine(timeout=1)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)
    result = engine.wait_for_decision(aid)
    assert result == "timeout"


def test_hitl_pending_status():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)
    assert engine.has_pending() is True
    engine.reject(aid)
    engine.wait_for_decision(aid)
    assert engine.has_pending() is False