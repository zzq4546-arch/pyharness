from pyharness.feedback import FeedbackCollector
from pyharness.config import ConfigLoader
from pyharness.models import ToolResult, Feedback


def test_collect_test_pass():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_tests", success=True,
                        output="10 passed", exit_code=0)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "PASS"
    assert fb.round == 1


def test_collect_test_fail():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_tests", success=False,
                        output="3 failed", error="AssertionError", exit_code=1)
    fb = collector.collect(result, round_num=2)
    assert fb.status == "FAIL"
    assert fb.round == 2
    assert len(fb.details) > 0


def test_collect_lint_pass():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_lint", success=True,
                        output="All checks passed!", exit_code=0)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "PASS"


def test_collect_lint_fail():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_lint", success=False,
                        output="Found 2 errors", error="E501 line too long", exit_code=1)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "FAIL"


def test_not_stuck_with_different_failures():
    collector = FeedbackCollector(ConfigLoader())
    feedbacks = [
        Feedback(status="FAIL", summary="error: import error", details=[{"error": "ImportError"}]),
        Feedback(status="FAIL", summary="error: assertion", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: type error", details=[{"error": "TypeError"}]),
    ]
    assert collector.is_stuck(feedbacks) is False


def test_stuck_with_same_failure():
    collector = FeedbackCollector(ConfigLoader())
    collector._config.load()
    collector._config._config["max_retries"] = 3
    feedbacks = [
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
    ]
    assert collector.is_stuck(feedbacks) is True


def test_collect_shell_error():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="execute_shell", success=False,
                        output="", error="command not found", exit_code=127)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "ERROR"