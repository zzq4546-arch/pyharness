import os
from typing import List, Optional
from pyharness.models import Message, Feedback
from pyharness.config import ConfigLoader
from pyharness.memory import MemoryStore


SYSTEM_PROMPT = """You are a coding agent. Your job is to complete programming tasks autonomously.

You have access to these tools:
- read_file(path): read a file's contents
- write_file(path, content): create or overwrite a file
- execute_shell(command): run a shell command
- run_tests(command): run tests (default: pytest)
- run_lint(path): run lint checks
- list_files(path): list directory contents

When you want to use a tool, respond with a JSON block:
```json
{"type": "tool_call", "tool_name": "<name>", "tool_args": {...}, "thought": "why I'm doing this"}
```

When the task is complete, respond with:
```json
{"type": "stop", "stop_reason": "task_complete", "thought": "summary of what was done"}
```

For any other response, just reply in plain text.

Always follow TDD: write tests first, then implementation.
"""


class ContextManager:
    def __init__(self, config: ConfigLoader, memory: MemoryStore, workspace: str):
        self._config = config
        self._memory = memory
        self._workspace = workspace

    def build_messages(self, user_task: str, history: List[Message],
                       feedback: Optional[Feedback]) -> List[Message]:
        messages = []
        messages.append(Message(role="system", content=self._build_system_prompt()))
        messages.append(Message(role="user", content=f"Workspace: {self._workspace}"))
        messages.append(Message(role="user", content=user_task))
        if feedback:
            messages.append(Message(
                role="user",
                content=f"[FEEDBACK] Round {feedback.round}: {feedback.status}\n{feedback.summary}"
            ))
        window = self._config.get("history_window", 20)
        if history:
            messages.extend(history[-window:])
        return messages

    def _build_system_prompt(self) -> str:
        prompt = SYSTEM_PROMPT
        entries = self._memory.list_all()
        if entries:
            prompt += "\n\n## Project Memory\n"
            for entry in entries:
                prompt += f"- [{entry.category}] {entry.content}\n"
        return prompt