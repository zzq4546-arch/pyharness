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
        match = re.search(r'\{[^{}]*"type"\s*:\s*"[^"]+"', text, re.DOTALL)
        if match:
            start = match.start()
            depth = 0
            end = start
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            candidate = text[start:end]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
        return None