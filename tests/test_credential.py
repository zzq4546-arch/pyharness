import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from pyharness.credential import CredentialManager


def _mock_keyring(get_password_return=None, get_password_side_effect=None):
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = get_password_return
    if get_password_side_effect:
        mock_kr.get_password.side_effect = get_password_side_effect
    return mock_kr


def test_credential_is_set_returns_false_when_empty():
    mock_kr = _mock_keyring(get_password_return=None)
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        assert manager.is_set() is False


def test_credential_is_set_returns_true_when_exists():
    mock_kr = _mock_keyring(get_password_return="sk-test-key")
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        assert manager.is_set() is True


def test_credential_get_returns_key():
    mock_kr = _mock_keyring(get_password_return="sk-test-key")
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        assert manager.get() == "sk-test-key"


def test_credential_set_stores_key():
    mock_kr = _mock_keyring(get_password_return=None)
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        manager.set("sk-new-key")
        mock_kr.set_password.assert_called_once_with("test_harness", "api_key", "sk-new-key")


def test_credential_clear_removes_key():
    mock_kr = _mock_keyring(get_password_return=None)
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        manager.clear()
        mock_kr.delete_password.assert_called_once_with("test_harness", "api_key")


def test_credential_get_returns_none_on_error():
    mock_kr = _mock_keyring(get_password_side_effect=Exception("keyring error"))
    with patch.dict(sys.modules, {"keyring": mock_kr}):
        manager = CredentialManager(service_name="test_harness")
        assert manager.get() is None