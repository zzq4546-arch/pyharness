import os
import yaml


DEFAULT_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "max_rounds": 10,
    "token_budget": 100000,
    "max_retries": 3,
    "approval_timeout": 120,
    "tool_timeout": 60,
    "history_window": 20,
    "guardrail": {
        "dangerous_commands": [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf ~",
            "rm -rf",
            "sudo rm",
            "chmod 777",
            "git push --force",
            "git push -f",
            "DROP TABLE",
            "DROP DATABASE",
            "shutdown",
            "reboot",
            ":(){ :|:& };:",
            "mkfs.",
            "dd if=",
            "> /dev/sda",
        ],
        "protected_files": [
            ".env",
            ".git/config",
            "*.key",
            "*.pem",
            "*.p12",
            "id_rsa",
            "id_ed25519",
        ],
        "approval_commands": [
            "curl",
            "wget",
            "pip install",
            "pip3 install",
            "npm install -g",
            "git clone",
            "git push",
            "git commit --amend",
            "git rebase",
        ],
        "approval_file_patterns": [
            "delete_many",
        ],
        "max_files_delete": 5,
    },
    "tools": {
        "enabled": ["read_file", "write_file", "execute_shell",
                     "run_tests", "run_lint", "list_files"],
    },
}


class ConfigLoader:
    def __init__(self, config_path: str = ".harness/config.yaml"):
        self.config_path = config_path
        self._config = DEFAULT_CONFIG.copy()

    def load(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            self._config = self._deep_merge(DEFAULT_CONFIG.copy(), user_config)
        else:
            self._config = DEFAULT_CONFIG.copy()
        return self._config

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                if k in value:
                    value = value[k]
                else:
                    return default
            else:
                return default
        return value

    def _deep_merge(self, base: dict, override: dict) -> dict:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base