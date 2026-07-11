import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pyharness.webui.server import create_app
from pyharness.llm import MockProvider
from pyharness.config import ConfigLoader


@pytest.fixture
def client():
    config = ConfigLoader()
    config.load()
    config._config["tools"]["enabled"] = ["read_file", "write_file", "execute_shell",
                                           "run_tests", "run_lint", "list_files"]
    app = create_app(config)
    return TestClient(app)


def test_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "idle"


def test_chat_endpoint_requires_task(client):
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


def test_approve_endpoint_when_nothing_pending(client):
    response = client.post("/api/approve", json={"approval_id": "fake", "decision": "approve"})
    assert response.status_code == 404