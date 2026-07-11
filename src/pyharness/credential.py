import os
import json
import base64
import hashlib
from typing import Optional


class CredentialManager:
    def __init__(self, service_name: str = "pyharness"):
        self._service_name = service_name
        self._username = "api_key"

    def is_set(self) -> bool:
        return self.get() is not None

    def get(self) -> Optional[str]:
        try:
            import keyring
            key = keyring.get_password(self._service_name, self._username)
            if key:
                return key
        except Exception:
            pass
        return self._get_from_encrypted_file()

    def set(self, key: str):
        try:
            import keyring
            keyring.set_password(self._service_name, self._username, key)
            return
        except Exception:
            pass
        self._save_to_encrypted_file(key)

    def update(self, key: str):
        self.set(key)

    def clear(self):
        try:
            import keyring
            keyring.delete_password(self._service_name, self._username)
        except Exception:
            pass
        enc_path = self._encrypted_file_path()
        if os.path.exists(enc_path):
            os.remove(enc_path)

    def _encrypted_file_path(self) -> str:
        home = os.path.expanduser("~")
        return os.path.join(home, ".harness", "key.enc")

    def _get_from_encrypted_file(self) -> Optional[str]:
        enc_path = self._encrypted_file_path()
        if not os.path.exists(enc_path):
            return None
        try:
            from cryptography.fernet import Fernet
            with open(enc_path, "r") as f:
                data = json.load(f)
            key = self._derive_key()
            f = Fernet(key)
            return f.decrypt(data["encrypted"].encode()).decode()
        except Exception:
            return None

    def _save_to_encrypted_file(self, api_key: str):
        enc_path = self._encrypted_file_path()
        os.makedirs(os.path.dirname(enc_path), exist_ok=True)
        try:
            from cryptography.fernet import Fernet
            key = self._derive_key()
            f = Fernet(key)
            encrypted = f.encrypt(api_key.encode()).decode()
            with open(enc_path, "w") as fp:
                json.dump({"encrypted": encrypted}, fp)
        except Exception:
            pass

    def _derive_key(self) -> bytes:
        machine_id = hashlib.sha256(
            os.environ.get("COMPUTERNAME", "pyharness").encode()
        ).digest()
        return base64.urlsafe_b64encode(machine_id)