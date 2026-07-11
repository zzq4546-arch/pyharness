import os
import tempfile
import yaml
from pyharness.config import ConfigLoader


def test_config_loader_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        loader = ConfigLoader(config_path)
        config = loader.load()
        assert config["max_rounds"] == 10
        assert config["model"] == "claude-sonnet-4-20250514"
        assert config["token_budget"] == 100000
        assert config["max_retries"] == 3
        assert config["approval_timeout"] == 120


def test_config_loader_custom_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump({"max_rounds": 5, "model": "claude-3-5-sonnet"}, f)
        loader = ConfigLoader(config_path)
        config = loader.load()
        assert config["max_rounds"] == 5
        assert config["model"] == "claude-3-5-sonnet"
        assert config["token_budget"] == 100000  # default not overridden


def test_config_loader_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        loader = ConfigLoader(config_path)
        loader.load()
        assert loader.get("max_rounds") == 10
        assert loader.get("nonexistent", "fallback") == "fallback"


def test_config_loader_guardrail_rules():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        loader = ConfigLoader(config_path)
        config = loader.load()
        assert "guardrail" in config
        assert "dangerous_commands" in config["guardrail"]
        assert "rm -rf" in config["guardrail"]["dangerous_commands"]


def test_config_loader_missing_file_uses_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "nonexistent.yaml")
        loader = ConfigLoader(config_path)
        config = loader.load()
        assert config["max_rounds"] == 10