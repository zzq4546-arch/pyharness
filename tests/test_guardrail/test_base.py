from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult


class MockGuard(Guard):
    def __init__(self, result: GuardResult):
        self._result = result

    def check(self, action: Action) -> GuardResult:
        return self._result


def test_guard_abstract_interface():
    guard = MockGuard(GuardResult(blocked=False, needs_approval=False, reason="", guard_name="MockGuard"))
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = guard.check(action)
    assert result.blocked is False
    assert result.guard_name == "MockGuard"