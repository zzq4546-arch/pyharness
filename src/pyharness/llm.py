from __future__ import annotations

from abc import ABC, abstractmethod

from pyharness.models import Message


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[Message]) -> str:
        ...


class MockProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = responses
        self._index = 0

    def chat(self, messages: list[Message]) -> str:
        if self._index >= len(self._responses):
            raise IndexError("MockProvider: no more responses")
        response = self._responses[self._index]
        self._index += 1
        return response


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key
        self._model = model

    def chat(self, messages: list[Message]) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                user_msgs.append({"role": m.role, "content": m.content})
        response = client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_msg if system_msg else None,
            messages=user_msgs,
        )
        return response.content[0].text