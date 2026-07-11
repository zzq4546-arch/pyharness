import os
import tempfile
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_scope_guard_allows_path_in_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        filepath = os.path.join(tmpdir, "test.py")
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": filepath, "content": "x"}, thought="")
        result = guard.check(action)
        assert result.blocked is False


def test_scope_guard_blocks_path_escape():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": os.path.join(tmpdir, "..", "etc", "passwd")},
                        thought="")
        result = guard.check(action)
        assert result.blocked is True
        assert "outside workspace" in result.reason.lower()


def test_scope_guard_blocks_absolute_escape():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": "/etc/passwd"}, thought="")
        result = guard.check(action)
        assert result.blocked is True


def test_scope_guard_blocks_env_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        guard._config.load()
        env_path = os.path.join(tmpdir, ".env")
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": env_path, "content": "KEY=secret"}, thought="")
        result = guard.check(action)
        assert result.blocked is True
        assert "protected" in result.reason.lower()


def test_scope_guard_blocks_key_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        guard._config.load()
        key_path = os.path.join(tmpdir, "secret.key")
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": key_path, "content": "key"}, thought="")
        result = guard.check(action)
        assert result.blocked is True


def test_scope_guard_skips_non_file_actions():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="execute_shell",
                        tool_args={"command": "ls"}, thought="")
        result = guard.check(action)
        assert result.blocked is False