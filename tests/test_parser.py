from pyharness.parser import ActionParser
from pyharness.models import Action


def test_parse_tool_call_json():
    parser = ActionParser()
    raw = """I will create a file.
```json
{"type": "tool_call", "tool_name": "write_file", "tool_args": {"path": "a.py", "content": "print(1)"}, "thought": "creating file"}
```"""
    action = parser.parse(raw)
    assert action.type == "tool_call"
    assert action.tool_name == "write_file"
    assert action.tool_args["path"] == "a.py"
    assert action.tool_args["content"] == "print(1)"


def test_parse_tool_call_inline_json():
    parser = ActionParser()
    raw = '{"type": "tool_call", "tool_name": "read_file", "tool_args": {"path": "b.py"}, "thought": "reading"}'
    action = parser.parse(raw)
    assert action.type == "tool_call"
    assert action.tool_name == "read_file"


def test_parse_stop():
    parser = ActionParser()
    raw = """Task is complete.
```json
{"type": "stop", "stop_reason": "task_complete", "thought": "all done"}
```"""
    action = parser.parse(raw)
    assert action.type == "stop"
    assert action.stop_reason == "task_complete"


def test_parse_response_fallback():
    parser = ActionParser()
    raw = "I think we should use pytest for this project."
    action = parser.parse(raw)
    assert action.type == "response"
    assert action.thought == raw
    assert action.tool_name is None


def test_parse_malformed_json_fallback():
    parser = ActionParser()
    raw = """```json
{"type": "tool_call", broken json
```"""
    action = parser.parse(raw)
    assert action.type == "response"
    assert "fallback" in action.thought.lower()