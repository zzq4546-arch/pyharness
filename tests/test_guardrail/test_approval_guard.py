from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_approval_guard_flags_pip_install():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pip install requests"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True
    assert "network" in result.reason.lower() or "install" in result.reason.lower()


def test_approval_guard_flags_curl():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl https://example.com"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True


def test_approval_guard_flags_git_push():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "git push origin main"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True


def test_approval_guard_allows_safe_command():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pytest tests/"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is False


def test_approval_guard_skips_non_shell():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "x"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is False