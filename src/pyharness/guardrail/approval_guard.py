from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class ApprovalGuard(Guard):
    def __init__(self, config: ConfigLoader):
        self._config = config

    def check(self, action: Action) -> GuardResult:
        if action.tool_name != "execute_shell":
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ApprovalGuard")
        command = (action.tool_args or {}).get("command", "")
        approval_patterns = self._config.get("guardrail.approval_commands", [])
        for pattern in approval_patterns:
            if pattern.lower() in command.lower():
                return GuardResult(
                    blocked=False, needs_approval=True,
                    reason=f"requires_approval: matched '{pattern}'",
                    guard_name="ApprovalGuard",
                )
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ApprovalGuard")