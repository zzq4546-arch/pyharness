import json
import re
from typing import Optional
from pyharness.models import Action


class ActionParser:
    def parse(self, raw_response: str) -> Action:
        json_block = self._extract_json(raw_response)
        if json_block:
            try:
                data = json.loads(json_block)
                return Action(
                    type=data.get("type", "response"),
                    tool_name=data.get("tool_name"),
                    tool_args=data.get("tool_args"),
                    thought=data.get("thought", raw_response[:200]),
                    stop_reason=data.get("stop_reason"),
                )
            except (json.JSONDecodeError, TypeError):
                return Action(
                    type="response",
                    thought="[fallback] " + raw_response,
                )
        return Action(
            type="response",
            thought=raw_response,
        )

    def _extract_json(self, text: str) -> Optional[str]:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        return None
        return None