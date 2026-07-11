from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_rule_guard_blocks_rm_rf():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "rm -rf /"}, thought="")
    result = guard.check(action)
    assert result.blocked is True
    assert "dangerous" in result.reason.lower()


def test_rule_guard_blocks_drop_table():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "DROP TABLE users"}, thought="")
    result = guard.check(action)
    assert result.blocked is True


def test_rule_guard_blocks_sudo():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "sudo rm file.txt"}, thought="")
    result = guard.check(action)
    assert result.blocked is True


def test_rule_guard_allows_safe_command():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pytest"}, thought="")
    result = guard.check(action)
    assert result.blocked is False


def test_rule_guard_skips_non_shell_actions():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "print(1)"}, thought="")
    result = guard.check(action)
    assert result.blocked is False


def test_rule_guard_blocks_fork_bomb():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": ":(){ :|:& };:"}, thought="")
    result = guard.check(action)
    assert result.blocked is True