from __future__ import annotations

from pyharness.models import Action, GuardResult
from pyharness.guardrail.base import Guard


class GuardrailChain:
    def __init__(self, guards: list[Guard]):
        self._guards = guards

    def check(self, action: Action) -> GuardResult:
        for guard in self._guards:
            result = guard.check(action)
            if result.blocked or result.needs_approval:
                return result
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="GuardrailChain")