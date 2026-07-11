import os
import tempfile
from pyharness.tools import ToolExecutor
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_read_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("hello world")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": filepath}, thought="")
        result = executor.execute(action)
        assert result.success is True
        assert result.output == "hello world"


def test_write_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "new.txt")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": filepath, "content": "new content"},
                        thought="")
        result = executor.execute(action)
        assert result.success is True
        with open(filepath) as f:
            assert f.read() == "new content"


def test_list_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "a.py"), "w") as f:
            f.write("")
        with open(os.path.join(tmpdir, "b.txt"), "w") as f:
            f.write("")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="list_files",
                        tool_args={"path": tmpdir}, thought="")
        result = executor.execute(action)
        assert result.success is True
        assert "a.py" in result.output
        assert "b.txt" in result.output
        assert "subdir" in result.output


def test_unknown_tool():
    executor = ToolExecutor(ConfigLoader(), workspace="/tmp")
    action = Action(type="tool_call", tool_name="unknown_tool",
                    tool_args={}, thought="")
    result = executor.execute(action)
    assert result.success is False
    assert "unknown" in result.error.lower()


def test_disabled_tool():
    config = ConfigLoader()
    config.load()
    config._config["tools"]["enabled"] = ["read_file"]
    executor = ToolExecutor(config, workspace="/tmp")
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "/tmp/test", "content": "x"}, thought="")
    result = executor.execute(action)
    assert result.success is False
    assert "disabled" in result.error.lower()