import os
import fnmatch
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class ScopeGuard(Guard):
    def __init__(self, config: ConfigLoader, workspace: str):
        self._config = config
        self._workspace = os.path.abspath(workspace)

    def check(self, action: Action) -> GuardResult:
        path = (action.tool_args or {}).get("path", "")
        if not path:
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ScopeGuard")

        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self._workspace + os.sep) and abs_path != self._workspace:
            return GuardResult(
                blocked=True, needs_approval=False,
                reason=f"path outside workspace: {path}",
                guard_name="ScopeGuard",
            )

        filename = os.path.basename(path)
        protected = self._config.get("guardrail.protected_files", [])
        for pattern in protected:
            if fnmatch.fnmatch(filename, pattern):
                return GuardResult(
                    blocked=True, needs_approval=False,
                    reason=f"protected file: matched pattern '{pattern}'",
                    guard_name="ScopeGuard",
                )

        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ScopeGuard")