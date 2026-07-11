import re
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class RuleGuard(Guard):
    def __init__(self, config: ConfigLoader):
        self._config = config

    def check(self, action: Action) -> GuardResult:
        if action.tool_name != "execute_shell":
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="RuleGuard")
        command = (action.tool_args or {}).get("command", "")
        dangerous = self._config.get("guardrail.dangerous_commands", [])
        for pattern in dangerous:
            try:
                if re.search(re.escape(pattern), command, re.IGNORECASE):
                    return GuardResult(
                        blocked=True, needs_approval=False,
                        reason=f"dangerous_command: matched pattern '{pattern}'",
                        guard_name="RuleGuard",
                    )
            except re.error:
                continue
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="RuleGuard")