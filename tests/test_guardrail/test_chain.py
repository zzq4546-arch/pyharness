from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult


class PassGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=False, needs_approval=False, reason="ok", guard_name="PassGuard")


class BlockGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=True, needs_approval=False, reason="blocked", guard_name="BlockGuard")


class ApproveGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=False, needs_approval=True, reason="needs approval", guard_name="ApproveGuard")


def test_chain_passes_when_all_guards_pass():
    chain = GuardrailChain([PassGuard(), PassGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is False
    assert result.needs_approval is False


def test_chain_stops_at_first_block():
    chain = GuardrailChain([PassGuard(), BlockGuard(), PassGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is True
    assert result.guard_name == "BlockGuard"


def test_chain_stops_at_first_approval():
    chain = GuardrailChain([PassGuard(), ApproveGuard(), BlockGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.needs_approval is True
    assert result.guard_name == "ApproveGuard"


def test_chain_empty_guards_passes():
    chain = GuardrailChain([])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is False
    assert result.needs_approval is False