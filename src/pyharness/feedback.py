from __future__ import annotations

from pyharness.models import ToolResult, Feedback
from pyharness.config import ConfigLoader


class FeedbackCollector:
    def __init__(self, config: ConfigLoader):
        self._config = config

    def collect(self, result: ToolResult, round_num: int) -> Feedback:
        if result.success:
            return Feedback(status="PASS", summary=result.output[:500], details=[], round=round_num)

        if result.tool_name in ("run_tests", "run_lint"):
            details = self._extract_failures(result)
            return Feedback(status="FAIL", summary=result.error or result.output[:500],
                            details=details, round=round_num)

        return Feedback(status="ERROR", summary=result.error or "unknown error",
                        details=[], round=round_num)

    def _extract_failures(self, result: ToolResult) -> list[dict]:
        details = []
        output = result.output + "\n" + (result.error or "")
        for line in output.split("\n"):
            line = line.strip()
            if line and ("FAILED" in line or "error" in line.lower() or "Error" in line):
                details.append({"error": line[:200]})
        return details[:20]

    def is_stuck(self, feedbacks: list[Feedback]) -> bool:
        max_retries = self._config.get("max_retries", 3)
        if len(feedbacks) < max_retries:
            return False
        recent = feedbacks[-max_retries:]
        if not all(f.status in ("FAIL", "ERROR") for f in recent):
            return False
        first_error = recent[0].summary
        return all(f.summary == first_error for f in recent)