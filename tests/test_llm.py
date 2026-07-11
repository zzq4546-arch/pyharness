from pyharness.models import Message
from pyharness.llm import MockProvider


def test_mock_provider_returns_responses_in_order():
    provider = MockProvider(responses=["hello", "world"])
    result1 = provider.chat([Message(role="user", content="hi")])
    result2 = provider.chat([Message(role="user", content="again")])
    assert result1 == "hello"
    assert result2 == "world"


def test_mock_provider_raises_when_exhausted():
    provider = MockProvider(responses=["only one"])
    provider.chat([Message(role="user", content="first")])
    try:
        provider.chat([Message(role="user", content="second")])
        assert False, "should have raised IndexError"
    except IndexError:
        pass


def test_mock_provider_with_empty_responses():
    provider = MockProvider(responses=[])
    try:
        provider.chat([Message(role="user", content="hi")])
        assert False, "should have raised IndexError"
    except IndexError:
        pass


def test_mock_provider_preserves_messages():
    provider = MockProvider(responses=["response"])
    msgs = [
        Message(role="system", content="you are a coder"),
        Message(role="user", content="write a test"),
    ]
    result = provider.chat(msgs)
    assert result == "response"