# PyHarness 实现计划

> **For agentic workers:** 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐 task 实现。步骤使用 `- [ ]` checkbox 语法跟踪。

**目标：** 构建一个 Python Coding Agent Harness，包含主循环、护栏、HITL、反馈闭环、记忆、配置六大机制，通过 Docker 分发，提供类终端 WebUI。

**架构：** 管道式架构，Agent 主循环为 `上下文组装 → LLM 调用 → 动作解析 → 护栏链检查 → (HITL审批) → 工具执行 → 反馈回灌 → 停机判断`。治理护栏为重点维度，三层拦截器链（Rule/Scope/Approval）。

**技术栈：** Python 3.12+, FastAPI, Anthropic SDK, keyring, pytest, Docker

## 全局约束

- Python >= 3.12
- 所有测试可单命令运行：`pytest`
- Mock LLM 必须覆盖所有核心机制测试
- 凭据绝不硬编码、不进 Git、不进日志
- 配置文件格式：YAML（`.harness/config.yaml`）
- 工作目录：默认当前目录，可通过配置覆盖
- 遵循 TDD：先写失败测试，再写实现

---

## 任务依赖关系

```
Phase 1 (基础):
  Task 1 (脚手架) ──► Task 2 (数据模型) ──► Task 3 (配置)
                           │
Phase 2 (核心模块):        │
  Task 4 (LLM) ◄───────────┤
  Task 5 (Parser) ◄────────┤  可并行
  Task 6 (工具) ◄──────────┘
       │
Phase 3 (护栏重点):        │
  Task 7 (护栏基类+链) ◄───┤
  Task 8 (RuleGuard) ◄─────┤  顺序依赖
  Task 9 (ScopeGuard) ◄────┤
  Task 10 (Approval+HITL) ◄┘
       │
Phase 4 (反馈+记忆):       │
  Task 11 (反馈) ◄─────────┤  可并行
  Task 12 (记忆) ◄─────────┘
       │
Phase 5 (集成):            │
  Task 13 (上下文) ◄───────┤
  Task 14 (主循环) ◄───────┤  顺序依赖
  Task 15 (凭据) ◄─────────┘
       │
Phase 6 (WebUI):           │
  Task 16 (后端) ◄─────────┤  顺序依赖
  Task 17 (前端) ◄─────────┘
       │
Phase 7 (交付): 可并行
  Task 18 (Docker)
  Task 19 (CI)
  Task 20 (机制演示)
  Task 21 (README)
```

---

### Task 1: 项目脚手架

**文件：**
- 创建：`pyproject.toml`
- 创建：`src/pyharness/__init__.py`
- 创建：`tests/__init__.py`
- 创建：`tests/test_models.py`（空文件，Task 2 填充）
- 创建：`src/pyharness/guardrail/__init__.py`
- 创建：`src/pyharness/webui/__init__.py`
- 创建：`tests/test_guardrail/__init__.py`
- 创建：`.gitignore`

**接口：** 无依赖

**产物：** 可安装的包结构

- [ ] **Step 1: 编写 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "pyharness"
version = "0.1.0"
description = "Coding Agent Harness - AI4SE Final Project"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.39.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "keyring>=25.0.0",
    "pyyaml>=6.0",
    "websockets>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: 创建所有目录和空 __init__.py**

```bash
mkdir -p src/pyharness/guardrail src/pyharness/webui/static tests/test_guardrail
touch src/pyharness/__init__.py src/pyharness/guardrail/__init__.py
touch src/pyharness/webui/__init__.py tests/__init__.py tests/test_guardrail/__init__.py
```

- [ ] **Step 3: 编写 .gitignore**

```
__pycache__/
*.pyc
*.pyo
.env
.harness/key.enc
*.key
*.pem
dist/
build/
*.egg-info/
.venv/
venv/
```

- [ ] **Step 4: 安装依赖并验证**

```bash
pip install -e ".[dev]"
python -c "import pyharness; print('OK')"
```

输出：`OK`

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml .gitignore src/ tests/
git commit -m "feat: project scaffolding with pyproject.toml and directory structure"
```

---

### Task 2: 数据模型

**文件：**
- 创建：`src/pyharness/models.py`
- 创建：`tests/test_models.py`

**接口：**
- 无外部依赖

**产物：**
- `Message` 数据类
- `Action` 数据类
- `GuardResult` 数据类
- `ToolResult` 数据类
- `Feedback` 数据类
- `MemoryEntry` 数据类
- `AgentState` 数据类

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_models.py
from dataclasses import asdict
from pyharness.models import (
    Message, Action, GuardResult, ToolResult, Feedback, MemoryEntry, AgentState
)


def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_call_id is None
    assert msg.tool_result is None


def test_message_with_tool():
    msg = Message(role="tool", content="", tool_call_id="call_1", tool_result="done")
    assert msg.tool_call_id == "call_1"
    assert msg.tool_result == "done"


def test_action_tool_call():
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "print(1)"},
                    thought="creating file")
    assert action.type == "tool_call"
    assert action.tool_name == "write_file"
    assert action.tool_args["path"] == "a.py"
    assert action.stop_reason is None


def test_action_stop():
    action = Action(type="stop", stop_reason="task_complete",
                    thought="done")
    assert action.type == "stop"
    assert action.stop_reason == "task_complete"


def test_guard_result_blocked():
    gr = GuardResult(blocked=True, needs_approval=False,
                     reason="dangerous command", guard_name="RuleGuard")
    assert gr.blocked is True
    assert gr.guard_name == "RuleGuard"


def test_guard_result_approval():
    gr = GuardResult(blocked=False, needs_approval=True,
                     reason="network request", guard_name="ApprovalGuard")
    assert gr.needs_approval is True


def test_tool_result_success():
    tr = ToolResult(tool_name="read_file", success=True,
                    output="file content", error=None, exit_code=0)
    assert tr.success is True
    assert tr.output == "file content"


def test_tool_result_failure():
    tr = ToolResult(tool_name="execute_shell", success=False,
                    output="", error="command not found", exit_code=127)
    assert tr.success is False
    assert tr.exit_code == 127


def test_feedback_pass():
    fb = Feedback(status="PASS", summary="all tests passed",
                  details=[], round=3)
    assert fb.status == "PASS"
    assert fb.round == 3


def test_feedback_fail():
    fb = Feedback(status="FAIL", summary="3 tests failed",
                  details=[{"test": "test_add", "error": "AssertionError"}],
                  round=2)
    assert fb.status == "FAIL"
    assert len(fb.details) == 1


def test_memory_entry():
    entry = MemoryEntry(id="mem_1", category="convention",
                        content="use pytest for testing",
                        keywords=["test", "pytest"])
    assert entry.category == "convention"
    assert "pytest" in entry.keywords
    assert entry.created_at is not None
    assert entry.updated_at is not None


def test_agent_state():
    state = AgentState(status="IDLE", current_round=0, max_rounds=10,
                       tokens_used=0, guardrail_blocks=0,
                       pending_approval=None)
    assert state.status == "IDLE"
    assert state.current_round == 0
    assert state.pending_approval is None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_models.py -v
```

预期：全部 FAIL（模块不存在）

- [ ] **Step 3: 编写数据模型实现**

```python
# src/pyharness/models.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_result: Optional[str] = None


@dataclass
class Action:
    type: str  # "tool_call" | "response" | "stop"
    thought: str
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    stop_reason: Optional[str] = None


@dataclass
class GuardResult:
    blocked: bool
    needs_approval: bool
    reason: str
    guard_name: str


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None


@dataclass
class Feedback:
    status: str  # "PASS" | "FAIL" | "ERROR"
    summary: str
    details: list = field(default_factory=list)
    round: int = 0


@dataclass
class MemoryEntry:
    id: str
    category: str  # "convention" | "decision" | "preference" | "error_pattern"
    content: str
    keywords: list = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentState:
    status: str  # "IDLE" | "THINKING" | "AWAITING_APPROVAL" | "EXECUTING" | "STOPPED"
    current_round: int = 0
    max_rounds: int = 10
    tokens_used: int = 0
    guardrail_blocks: int = 0
    pending_approval: Optional[Action] = None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_models.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/models.py tests/test_models.py
git commit -m "feat: data models (Message, Action, GuardResult, ToolResult, Feedback, MemoryEntry, AgentState)"
```

---

### Task 3: 配置加载器

**文件：**
- 创建：`src/pyharness/config.py`
- 创建：`tests/test_config.py`

**消耗：** `models.py` 中的类型（无直接引用）

**接口：**
- 产生：`ConfigLoader` 类
  - `__init__(config_path: str = ".harness/config.yaml")`
  - `load() -> dict`
  - `get(key: str, default=None) -> Any`

**产物：** 可以从 YAML 文件加载配置，提供默认值

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_config.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/config.py
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
        self._config = {}

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
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def _deep_merge(self, base: dict, override: dict) -> dict:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_config.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/config.py tests/test_config.py
git commit -m "feat: ConfigLoader with YAML support and defaults"
```

---

### Task 4: LLM 抽象层

**文件：**
- 创建：`src/pyharness/llm.py`
- 创建：`tests/test_llm.py`

**消耗：** `models.py` 的 `Message` 类型

**接口：**
- 产生：`LLMProvider` 抽象基类
  - `chat(messages: list[Message]) -> str`
- 产生：`MockProvider(LLMProvider)`
  - `__init__(responses: list[str])`
  - `chat(messages: list[Message]) -> str`
- 产生：`AnthropicProvider(LLMProvider)`（依赖真实 API，测试中不验证）

**产物：** 可注入 mock 的 LLM 抽象层，`MockProvider` 按序返回预设响应

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_llm.py
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
        assert False, "should have raised StopIteration"
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_llm.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/llm.py
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_llm.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/llm.py tests/test_llm.py
git commit -m "feat: LLM abstraction layer with MockProvider and AnthropicProvider"
```

---

### Task 5: 动作解析器

**文件：**
- 创建：`src/pyharness/parser.py`
- 创建：`tests/test_parser.py`

**消耗：** `models.py` 的 `Action` 类型

**接口：**
- 产生：`ActionParser` 类
  - `parse(raw_response: str) -> Action`

**产物：** 将 LLM 原始文本解析为结构化 Action

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_parser.py
from pyharness.parser import ActionParser
from pyharness.models import Action


def test_parse_tool_call_json():
    parser = ActionParser()
    raw = """I will create a file.
```json
{"type": "tool_call", "tool_name": "write_file", "tool_args": {"path": "a.py", "content": "print(1)"}, "thought": "creating file"}
```"""
    action = parser.parse(raw)
    assert action.type == "tool_call"
    assert action.tool_name == "write_file"
    assert action.tool_args["path"] == "a.py"
    assert action.tool_args["content"] == "print(1)"


def test_parse_tool_call_inline_json():
    parser = ActionParser()
    raw = '{"type": "tool_call", "tool_name": "read_file", "tool_args": {"path": "b.py"}, "thought": "reading"}'
    action = parser.parse(raw)
    assert action.type == "tool_call"
    assert action.tool_name == "read_file"


def test_parse_stop():
    parser = ActionParser()
    raw = """Task is complete.
```json
{"type": "stop", "stop_reason": "task_complete", "thought": "all done"}
```"""
    action = parser.parse(raw)
    assert action.type == "stop"
    assert action.stop_reason == "task_complete"


def test_parse_response_fallback():
    parser = ActionParser()
    raw = "I think we should use pytest for this project."
    action = parser.parse(raw)
    assert action.type == "response"
    assert action.thought == raw
    assert action.tool_name is None


def test_parse_malformed_json_fallback():
    parser = ActionParser()
    raw = """```json
{"type": "tool_call", broken json
```"""
    action = parser.parse(raw)
    assert action.type == "response"
    assert "fallback" in action.thought.lower()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_parser.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/parser.py
import json
import re
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
                pass
        return Action(
            type="response",
            thought=raw_response,
        )

    def _extract_json(self, text: str) -> str | None:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r'\{[^{}]*"type"\s*:\s*"[^"]+"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                json.loads(match.group(0))
                return match.group(0)
            except json.JSONDecodeError:
                pass
        return None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_parser.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/parser.py tests/test_parser.py
git commit -m "feat: ActionParser with JSON extraction and fallback"
```

---

### Task 6: 工具执行器

**文件：**
- 创建：`src/pyharness/tools.py`
- 创建：`tests/test_tools.py`

**消耗：** `models.py` 的 `Action`、`ToolResult`

**接口：**
- 产生：`ToolExecutor` 类
  - `__init__(config: ConfigLoader, workspace: str)`
  - `execute(action: Action) -> ToolResult`

**产物：** 可执行 6 种工具的 ToolExecutor，带超时和工作区限制

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_tools.py
import os
import tempfile
from pyharness.tools import ToolExecutor
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_read_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("hello world")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": filepath}, thought="")
        result = executor.execute(action)
        assert result.success is True
        assert result.output == "hello world"


def test_write_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "new.txt")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": filepath, "content": "new content"},
                        thought="")
        result = executor.execute(action)
        assert result.success is True
        with open(filepath) as f:
            assert f.read() == "new content"


def test_list_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "a.py"), "w") as f:
            f.write("")
        with open(os.path.join(tmpdir, "b.txt"), "w") as f:
            f.write("")
        executor = ToolExecutor(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="list_files",
                        tool_args={"path": tmpdir}, thought="")
        result = executor.execute(action)
        assert result.success is True
        assert "a.py" in result.output
        assert "b.txt" in result.output
        assert "subdir" in result.output


def test_unknown_tool():
    executor = ToolExecutor(ConfigLoader(), workspace="/tmp")
    action = Action(type="tool_call", tool_name="unknown_tool",
                    tool_args={}, thought="")
    result = executor.execute(action)
    assert result.success is False
    assert "unknown" in result.error.lower()


def test_disabled_tool():
    config = ConfigLoader()
    config.load()
    config._config["tools"]["enabled"] = ["read_file"]
    executor = ToolExecutor(config, workspace="/tmp")
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "/tmp/test", "content": "x"}, thought="")
    result = executor.execute(action)
    assert result.success is False
    assert "disabled" in result.error.lower()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_tools.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/tools.py
import os
import subprocess
from pyharness.models import Action, ToolResult
from pyharness.config import ConfigLoader


class ToolExecutor:
    def __init__(self, config: ConfigLoader, workspace: str):
        self._config = config
        self._workspace = workspace

    def execute(self, action: Action) -> ToolResult:
        enabled = self._config.get("tools.enabled", [])
        if action.tool_name not in enabled:
            return ToolResult(
                tool_name=action.tool_name,
                success=False,
                output="",
                error=f"Tool '{action.tool_name}' is disabled",
            )

        handler = getattr(self, f"_handle_{action.tool_name}", None)
        if handler is None:
            return ToolResult(
                tool_name=action.tool_name,
                success=False,
                output="",
                error=f"Unknown tool: {action.tool_name}",
            )
        return handler(action.tool_args or {})

    def _handle_read_file(self, args: dict) -> ToolResult:
        path = args.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(tool_name="read_file", success=True, output=content)
        except Exception as e:
            return ToolResult(tool_name="read_file", success=False, output="", error=str(e))

    def _handle_write_file(self, args: dict) -> ToolResult:
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(tool_name="write_file", success=True, output=f"Written to {path}")
        except Exception as e:
            return ToolResult(tool_name="write_file", success=False, output="", error=str(e))

    def _handle_execute_shell(self, args: dict) -> ToolResult:
        command = args.get("command", "")
        timeout = self._config.get("tool_timeout", 60)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self._workspace,
            )
            return ToolResult(
                tool_name="execute_shell",
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name="execute_shell",
                success=False, output="",
                error=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(tool_name="execute_shell", success=False, output="", error=str(e))

    def _handle_run_tests(self, args: dict) -> ToolResult:
        command = args.get("command", "pytest")
        return self._handle_execute_shell({"command": command})

    def _handle_run_lint(self, args: dict) -> ToolResult:
        target = args.get("path", ".")
        command = f"ruff check {target}" if args.get("path") else "ruff check ."
        return self._handle_execute_shell({"command": command})

    def _handle_list_files(self, args: dict) -> ToolResult:
        path = args.get("path", self._workspace)
        try:
            entries = os.listdir(path)
            lines = []
            for entry in sorted(entries):
                full = os.path.join(path, entry)
                suffix = "/" if os.path.isdir(full) else ""
                lines.append(entry + suffix)
            return ToolResult(tool_name="list_files", success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(tool_name="list_files", success=False, output="", error=str(e))
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_tools.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/tools.py tests/test_tools.py
git commit -m "feat: ToolExecutor with 6 tools (read/write/shell/test/lint/list)"
```

---

### Task 7: 护栏基类与护栏链

**文件：**
- 创建：`src/pyharness/guardrail/base.py`
- 创建：`src/pyharness/guardrail/chain.py`
- 创建：`tests/test_guardrail/test_base.py`
- 创建：`tests/test_guardrail/test_chain.py`

**消耗：** `models.py` 的 `Action`、`GuardResult`；`config.py` 的 `ConfigLoader`

**接口：**
- 产生：`Guard` 抽象基类
  - `check(action: Action) -> GuardResult`
- 产生：`GuardrailChain` 类
  - `__init__(guards: list[Guard])`
  - `check(action: Action) -> GuardResult`

**产物：** 可组合的拦截器链，任一 guard 拦截即停止

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_guardrail/test_base.py
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult


class MockGuard(Guard):
    def __init__(self, result: GuardResult):
        self._result = result

    def check(self, action: Action) -> GuardResult:
        return self._result


def test_guard_abstract_interface():
    guard = MockGuard(GuardResult(blocked=False, needs_approval=False, reason="", guard_name="MockGuard"))
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = guard.check(action)
    assert result.blocked is False
    assert result.guard_name == "MockGuard"
```

```python
# tests/test_guardrail/test_chain.py
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult


class PassGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=False, needs_approval=False, reason="ok", guard_name="PassGuard")


class BlockGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=True, needs_approval=False, reason="blocked", guard_name="BlockGuard")


class ApproveGuard(Guard):
    def check(self, action: Action) -> GuardResult:
        return GuardResult(blocked=False, needs_approval=True, reason="needs approval", guard_name="ApproveGuard")


def test_chain_passes_when_all_guards_pass():
    chain = GuardrailChain([PassGuard(), PassGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is False
    assert result.needs_approval is False


def test_chain_stops_at_first_block():
    chain = GuardrailChain([PassGuard(), BlockGuard(), PassGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is True
    assert result.guard_name == "BlockGuard"


def test_chain_stops_at_first_approval():
    chain = GuardrailChain([PassGuard(), ApproveGuard(), BlockGuard()])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.needs_approval is True
    assert result.guard_name == "ApproveGuard"


def test_chain_empty_guards_passes():
    chain = GuardrailChain([])
    action = Action(type="tool_call", tool_name="test", tool_args={}, thought="")
    result = chain.check(action)
    assert result.blocked is False
    assert result.needs_approval is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail/ -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/guardrail/base.py
from abc import ABC, abstractmethod
from pyharness.models import Action, GuardResult


class Guard(ABC):
    @abstractmethod
    def check(self, action: Action) -> GuardResult:
        ...
```

```python
# src/pyharness/guardrail/chain.py
from pyharness.models import Action, GuardResult
from pyharness.guardrail.base import Guard


class GuardrailChain:
    def __init__(self, guards: list[Guard]):
        self._guards = guards

    def check(self, action: Action) -> GuardResult:
        for guard in self._guards:
            result = guard.check(action)
            if result.blocked or result.needs_approval:
                return result
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="GuardrailChain")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail/ -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/guardrail/base.py src/pyharness/guardrail/chain.py tests/test_guardrail/
git commit -m "feat: Guard base class and GuardrailChain with chain-of-responsibility pattern"
```

---

### Task 8: 规则护栏（RuleGuard）

**文件：**
- 创建：`src/pyharness/guardrail/rule_guard.py`
- 创建：`tests/test_guardrail/test_rule_guard.py`

**消耗：** `guardrail/base.py` 的 `Guard`；`config.py` 的 `ConfigLoader`

**接口：**
- 产生：`RuleGuard(Guard)`
  - `__init__(config: ConfigLoader)`
  - `check(action: Action) -> GuardResult`

**产物：** 正则匹配命令黑名单，确定性拦截危险命令

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_guardrail/test_rule_guard.py
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_rule_guard_blocks_rm_rf():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "rm -rf /"}, thought="")
    result = guard.check(action)
    assert result.blocked is True
    assert "dangerous" in result.reason.lower()


def test_rule_guard_blocks_drop_table():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "DROP TABLE users"}, thought="")
    result = guard.check(action)
    assert result.blocked is True


def test_rule_guard_blocks_sudo():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "sudo rm file.txt"}, thought="")
    result = guard.check(action)
    assert result.blocked is True


def test_rule_guard_allows_safe_command():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pytest"}, thought="")
    result = guard.check(action)
    assert result.blocked is False


def test_rule_guard_skips_non_shell_actions():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "print(1)"}, thought="")
    result = guard.check(action)
    assert result.blocked is False


def test_rule_guard_blocks_fork_bomb():
    guard = RuleGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": ":(){ :|:& };:"}, thought="")
    result = guard.check(action)
    assert result.blocked is True
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail/test_rule_guard.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/guardrail/rule_guard.py
import re
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class RuleGuard(Guard):
    def __init__(self, config: ConfigLoader):
        self._config = config

    def check(self, action: Action) -> GuardResult:
        if action.tool_name != "execute_shell":
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="RuleGuard")
        command = (action.tool_args or {}).get("command", "")
        dangerous = self._config.get("guardrail.dangerous_commands", [])
        for pattern in dangerous:
            try:
                if re.search(re.escape(pattern), command, re.IGNORECASE):
                    return GuardResult(
                        blocked=True, needs_approval=False,
                        reason=f"dangerous_command: matched pattern '{pattern}'",
                        guard_name="RuleGuard",
                    )
            except re.error:
                continue
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="RuleGuard")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail/test_rule_guard.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/guardrail/rule_guard.py tests/test_guardrail/test_rule_guard.py
git commit -m "feat: RuleGuard with regex-based dangerous command blacklist"
```

---

### Task 9: 范围护栏（ScopeGuard）

**文件：**
- 创建：`src/pyharness/guardrail/scope_guard.py`
- 创建：`tests/test_guardrail/test_scope_guard.py`

**消耗：** `guardrail/base.py` 的 `Guard`；`config.py` 的 `ConfigLoader`

**接口：**
- 产生：`ScopeGuard(Guard)`
  - `__init__(config: ConfigLoader, workspace: str)`
  - `check(action: Action) -> GuardResult`

**产物：** 路径规范化 + 前缀检查，防逃逸，保护敏感文件

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_guardrail/test_scope_guard.py
import os
import tempfile
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_scope_guard_allows_path_in_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        filepath = os.path.join(tmpdir, "test.py")
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": filepath, "content": "x"}, thought="")
        result = guard.check(action)
        assert result.blocked is False


def test_scope_guard_blocks_path_escape():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": os.path.join(tmpdir, "..", "etc", "passwd")},
                        thought="")
        result = guard.check(action)
        assert result.blocked is True
        assert "outside workspace" in result.reason.lower()


def test_scope_guard_blocks_absolute_escape():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader(), workspace=tmpdir)
        action = Action(type="tool_call", tool_name="read_file",
                        tool_args={"path": "/etc/passwd"}, thought="")
        result = guard.check(action)
        assert result.blocked is True


def test_scope_guard_blocks_env_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = ScopeGuard(ConfigLoader())
        guard._config.load()
        env_path = os.path.join(tmpdir, ".env")
        action = Action(type="tool_call", tool_name="write_file",
                        tool_args={"path": env_path, "content": "KEY=secret"}, thought="")
        result = guard.check(action)
        assert result.blocked is True
        assert "protected" in result.reason.lower()


def test_scope_guard_blocks_key_file():
    guard = ScopeGuard(ConfigLoader(), workspace="/tmp")
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "/tmp/secret.key", "content": "key"}, thought="")
    result = guard.check(action)
    assert result.blocked is True


def test_scope_guard_skips_non_file_actions():
    guard = ScopeGuard(ConfigLoader(), workspace="/tmp")
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "ls"}, thought="")
    result = guard.check(action)
    assert result.blocked is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail/test_scope_guard.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/guardrail/scope_guard.py
import os
import fnmatch
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class ScopeGuard(Guard):
    def __init__(self, config: ConfigLoader, workspace: str):
        self._config = config
        self._workspace = os.path.abspath(workspace)

    def check(self, action: Action) -> GuardResult:
        path = (action.tool_args or {}).get("path", "")
        if not path:
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ScopeGuard")

        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self._workspace + os.sep) and abs_path != self._workspace:
            return GuardResult(
                blocked=True, needs_approval=False,
                reason=f"path outside workspace: {path}",
                guard_name="ScopeGuard",
            )

        filename = os.path.basename(path)
        protected = self._config.get("guardrail.protected_files", [])
        for pattern in protected:
            if fnmatch.fnmatch(filename, pattern):
                return GuardResult(
                    blocked=True, needs_approval=False,
                    reason=f"protected file: matched pattern '{pattern}'",
                    guard_name="ScopeGuard",
                )

        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ScopeGuard")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail/test_scope_guard.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/guardrail/scope_guard.py tests/test_guardrail/test_scope_guard.py
git commit -m "feat: ScopeGuard with workspace boundary and protected file checks"
```

---

### Task 10: 审批护栏 + HITL 状态机

**文件：**
- 创建：`src/pyharness/guardrail/approval_guard.py`
- 创建：`src/pyharness/hitl.py`
- 创建：`tests/test_guardrail/test_approval_guard.py`
- 创建：`tests/test_hitl.py`

**消耗：** `guardrail/base.py` 的 `Guard`；`config.py` 的 `ConfigLoader`；`models.py` 的 `Action`

**接口：**
- 产生：`ApprovalGuard(Guard)`
  - `__init__(config: ConfigLoader)`
  - `check(action: Action) -> GuardResult`
- 产生：`HITLEngine`
  - `__init__(timeout: int = 120)`
  - `request_approval(action: Action) -> str`（返回 approval_id）
  - `wait_for_decision(approval_id: str) -> str`（"approved"/"rejected"/"timeout"）
  - `approve(approval_id: str)` / `reject(approval_id: str)`

**产物：** 审批护栏 + 带超时机制的 HITL 状态机

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_guardrail/test_approval_guard.py
from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.config import ConfigLoader
from pyharness.models import Action


def test_approval_guard_flags_pip_install():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pip install requests"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True
    assert "network" in result.reason.lower() or "install" in result.reason.lower()


def test_approval_guard_flags_curl():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl https://example.com"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True


def test_approval_guard_flags_git_push():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "git push origin main"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is True


def test_approval_guard_allows_safe_command():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pytest tests/"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is False


def test_approval_guard_skips_non_shell():
    guard = ApprovalGuard(ConfigLoader())
    guard._config.load()
    action = Action(type="tool_call", tool_name="write_file",
                    tool_args={"path": "a.py", "content": "x"}, thought="")
    result = guard.check(action)
    assert result.needs_approval is False
```

```python
# tests/test_hitl.py
import time
import threading
from pyharness.hitl import HITLEngine
from pyharness.models import Action


def test_hitl_approve_flow():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "pip install x"}, thought="")
    aid = engine.request_approval(action)

    def approve():
        engine.approve(aid)
    threading.Thread(target=approve).start()

    result = engine.wait_for_decision(aid)
    assert result == "approved"


def test_hitl_reject_flow():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)

    def reject():
        engine.reject(aid)
    threading.Thread(target=reject).start()

    result = engine.wait_for_decision(aid)
    assert result == "rejected"


def test_hitl_timeout_defaults_to_reject():
    engine = HITLEngine(timeout=1)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)
    result = engine.wait_for_decision(aid)
    assert result == "timeout"


def test_hitl_pending_status():
    engine = HITLEngine(timeout=30)
    action = Action(type="tool_call", tool_name="execute_shell",
                    tool_args={"command": "curl x"}, thought="")
    aid = engine.request_approval(action)
    assert engine.has_pending() is True
    engine.reject(aid)
    engine.wait_for_decision(aid)
    assert engine.has_pending() is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail/test_approval_guard.py tests/test_hitl.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/guardrail/approval_guard.py
from pyharness.guardrail.base import Guard
from pyharness.models import Action, GuardResult
from pyharness.config import ConfigLoader


class ApprovalGuard(Guard):
    def __init__(self, config: ConfigLoader):
        self._config = config

    def check(self, action: Action) -> GuardResult:
        if action.tool_name != "execute_shell":
            return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ApprovalGuard")
        command = (action.tool_args or {}).get("command", "")
        approval_patterns = self._config.get("guardrail.approval_commands", [])
        for pattern in approval_patterns:
            if pattern.lower() in command.lower():
                return GuardResult(
                    blocked=False, needs_approval=True,
                    reason=f"requires_approval: matched '{pattern}'",
                    guard_name="ApprovalGuard",
                )
        return GuardResult(blocked=False, needs_approval=False, reason="", guard_name="ApprovalGuard")
```

```python
# src/pyharness/hitl.py
import threading
import uuid
from pyharness.models import Action


class HITLEngine:
    def __init__(self, timeout: int = 120):
        self._timeout = timeout
        self._pending: dict[str, dict] = {}
        self._lock = threading.Lock()

    def request_approval(self, action: Action) -> str:
        approval_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._pending[approval_id] = {
                "action": action,
                "event": threading.Event(),
                "result": "pending",
            }
        return approval_id

    def wait_for_decision(self, approval_id: str) -> str:
        with self._lock:
            entry = self._pending.get(approval_id)
            if not entry:
                return "timeout"
        event = entry["event"]
        decided = event.wait(timeout=self._timeout)
        with self._lock:
            if not decided:
                entry["result"] = "timeout"
                event.set()
            result = entry["result"]
            del self._pending[approval_id]
        return result

    def approve(self, approval_id: str):
        with self._lock:
            entry = self._pending.get(approval_id)
            if entry and entry["result"] == "pending":
                entry["result"] = "approved"
                entry["event"].set()

    def reject(self, approval_id: str):
        with self._lock:
            entry = self._pending.get(approval_id)
            if entry and entry["result"] == "pending":
                entry["result"] = "rejected"
                entry["event"].set()

    def has_pending(self) -> bool:
        with self._lock:
            return len(self._pending) > 0
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail/test_approval_guard.py tests/test_hitl.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/guardrail/approval_guard.py src/pyharness/hitl.py tests/test_guardrail/test_approval_guard.py tests/test_hitl.py
git commit -m "feat: ApprovalGuard and HITL engine with timeout-default-reject"
```

---

### Task 11: 反馈收集器

**文件：**
- 创建：`src/pyharness/feedback.py`
- 创建：`tests/test_feedback.py`

**消耗：** `models.py` 的 `ToolResult`、`Feedback`

**接口：**
- 产生：`FeedbackCollector` 类
  - `__init__(config: ConfigLoader)`
  - `collect(result: ToolResult, round_num: int) -> Feedback`
  - `is_stuck(feedbacks: list[Feedback]) -> bool`

**产物：** 解析工具执行结果，判定 PASS/FAIL/ERROR，检测连续失败

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_feedback.py
from pyharness.feedback import FeedbackCollector
from pyharness.config import ConfigLoader
from pyharness.models import ToolResult, Feedback


def test_collect_test_pass():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_tests", success=True,
                        output="10 passed", exit_code=0)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "PASS"
    assert fb.round == 1


def test_collect_test_fail():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_tests", success=False,
                        output="3 failed", error="AssertionError", exit_code=1)
    fb = collector.collect(result, round_num=2)
    assert fb.status == "FAIL"
    assert fb.round == 2
    assert len(fb.details) > 0


def test_collect_lint_pass():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_lint", success=True,
                        output="All checks passed!", exit_code=0)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "PASS"


def test_collect_lint_fail():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="run_lint", success=False,
                        output="Found 2 errors", error="E501 line too long", exit_code=1)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "FAIL"


def test_not_stuck_with_different_failures():
    collector = FeedbackCollector(ConfigLoader())
    feedbacks = [
        Feedback(status="FAIL", summary="error: import error", details=[{"error": "ImportError"}]),
        Feedback(status="FAIL", summary="error: assertion", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: type error", details=[{"error": "TypeError"}]),
    ]
    assert collector.is_stuck(feedbacks) is False


def test_stuck_with_same_failure():
    collector = FeedbackCollector(ConfigLoader())
    collector._config.load()
    collector._config._config["max_retries"] = 3
    feedbacks = [
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
        Feedback(status="FAIL", summary="error: AssertionError: assert 1 == 2", details=[{"error": "AssertionError"}]),
    ]
    assert collector.is_stuck(feedbacks) is True


def test_collect_shell_error():
    collector = FeedbackCollector(ConfigLoader())
    result = ToolResult(tool_name="execute_shell", success=False,
                        output="", error="command not found", exit_code=127)
    fb = collector.collect(result, round_num=1)
    assert fb.status == "ERROR"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_feedback.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/feedback.py
from pyharness.models import ToolResult, Feedback
from pyharness.config import ConfigLoader


class FeedbackCollector:
    def __init__(self, config: ConfigLoader):
        self._config = config

    def collect(self, result: ToolResult, round_num: int) -> Feedback:
        if result.success:
            return Feedback(status="PASS", summary=result.output[:500], details=[], round=round_num)

        if result.tool_name in ("run_tests", "run_lint"):
            details = self._extract_failures(result)
            return Feedback(status="FAIL", summary=result.error or result.output[:500],
                            details=details, round=round_num)

        return Feedback(status="ERROR", summary=result.error or "unknown error",
                        details=[], round=round_num)

    def _extract_failures(self, result: ToolResult) -> list[dict]:
        details = []
        output = result.output + "\n" + (result.error or "")
        for line in output.split("\n"):
            line = line.strip()
            if line and ("FAILED" in line or "error" in line.lower() or "Error" in line):
                details.append({"error": line[:200]})
        return details[:20]

    def is_stuck(self, feedbacks: list[Feedback]) -> bool:
        max_retries = self._config.get("max_retries", 3)
        if len(feedbacks) < max_retries:
            return False
        recent = feedbacks[-max_retries:]
        if not all(f.status in ("FAIL", "ERROR") for f in recent):
            return False
        first_error = recent[0].summary
        return all(f.summary == first_error for f in recent)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_feedback.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/feedback.py tests/test_feedback.py
git commit -m "feat: FeedbackCollector with test/lint result parsing and stuck detection"
```

---

### Task 12: 记忆存储

**文件：**
- 创建：`src/pyharness/memory.py`
- 创建：`tests/test_memory.py`

**消耗：** `models.py` 的 `MemoryEntry`

**接口：**
- 产生：`MemoryStore` 类
  - `__init__(storage_dir: str = ".harness/memory")`
  - `add(entry: MemoryEntry)`
  - `search(query: str) -> list[MemoryEntry]`
  - `list_all() -> list[MemoryEntry]`
  - `delete(entry_id: str)`

**产物：** 基于 JSON 文件的记忆存储，支持关键词检索

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_memory.py
import os
import tempfile
from pyharness.memory import MemoryStore
from pyharness.models import MemoryEntry


def test_memory_add_and_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        entry = MemoryEntry(id="mem_1", category="convention",
                            content="Use pytest for all tests",
                            keywords=["test", "pytest"])
        store.add(entry)
        entries = store.list_all()
        assert len(entries) == 1
        assert entries[0].content == "Use pytest for all tests"


def test_memory_search_by_keyword():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="Use pytest", keywords=["test"]))
        store.add(MemoryEntry(id="2", category="decision",
                              content="Use FastAPI", keywords=["web"]))
        results = store.search("pytest")
        assert len(results) == 1
        assert results[0].id == "1"


def test_memory_search_by_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="Always use type hints", keywords=["typing"]))
        results = store.search("type hints")
        assert len(results) == 1


def test_memory_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(storage_dir=os.path.join(tmpdir, "memory"))
        store.add(MemoryEntry(id="1", category="convention",
                              content="test", keywords=[]))
        store.delete("1")
        assert len(store.list_all()) == 0


def test_memory_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem_dir = os.path.join(tmpdir, "memory")
        store1 = MemoryStore(storage_dir=mem_dir)
        store1.add(MemoryEntry(id="1", category="preference",
                               content="Prefer black formatting", keywords=["format"]))
        store2 = MemoryStore(storage_dir=mem_dir)
        entries = store2.list_all()
        assert len(entries) == 1
        assert entries[0].content == "Prefer black formatting"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_memory.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/memory.py
import os
import json
from pyharness.models import MemoryEntry


class MemoryStore:
    def __init__(self, storage_dir: str = ".harness/memory"):
        self._storage_dir = storage_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    def add(self, entry: MemoryEntry):
        filepath = os.path.join(self._storage_dir, f"{entry.id}.json")
        data = {
            "id": entry.id,
            "category": entry.category,
            "content": entry.content,
            "keywords": entry.keywords,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_all(self) -> list[MemoryEntry]:
        entries = []
        if not os.path.exists(self._storage_dir):
            return entries
        for filename in os.listdir(self._storage_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self._storage_dir, filename)
                entry = self._load_entry(filepath)
                if entry:
                    entries.append(entry)
        return entries

    def search(self, query: str) -> list[MemoryEntry]:
        query_lower = query.lower()
        results = []
        for entry in self.list_all():
            if query_lower in entry.content.lower():
                results.append(entry)
                continue
            for kw in entry.keywords:
                if query_lower in kw.lower():
                    results.append(entry)
                    break
        return results

    def delete(self, entry_id: str):
        filepath = os.path.join(self._storage_dir, f"{entry_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def _load_entry(self, filepath: str) -> MemoryEntry | None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            from datetime import datetime
            return MemoryEntry(
                id=data["id"],
                category=data["category"],
                content=data["content"],
                keywords=data.get("keywords", []),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )
        except (json.JSONDecodeError, KeyError):
            return None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_memory.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/memory.py tests/test_memory.py
git commit -m "feat: MemoryStore with JSON file persistence and keyword search"
```

---

### Task 13: 上下文管理器

**文件：**
- 创建：`src/pyharness/context.py`
- 创建：`tests/test_context.py`

**消耗：** `models.py` 的 `Message`、`Feedback`；`memory.py` 的 `MemoryStore`；`config.py` 的 `ConfigLoader`

**接口：**
- 产生：`ContextManager` 类
  - `__init__(config: ConfigLoader, memory: MemoryStore, workspace: str)`
  - `build_messages(user_task: str, history: list[Message], feedback: Feedback | None) -> list[Message]`

**产物：** 组装系统提示 + 对话历史 + 反馈 + 项目信息，控制 token 预算

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_context.py
import os
import tempfile
from pyharness.context import ContextManager
from pyharness.config import ConfigLoader
from pyharness.memory import MemoryStore
from pyharness.models import Message, Feedback, MemoryEntry


def test_build_messages_with_task():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("write a calculator", [], None)
        assert len(msgs) >= 2
        assert any(m.role == "system" for m in msgs)
        assert any(m.role == "user" and "write a calculator" in m.content for m in msgs)


def test_build_messages_with_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        history = [
            Message(role="user", content="write a test"),
            Message(role="assistant", content="ok"),
        ]
        msgs = ctx.build_messages("fix the test", history, None)
        assert len(msgs) >= 4


def test_build_messages_with_feedback():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        fb = Feedback(status="FAIL", summary="test_add failed: AssertionError",
                      details=[{"error": "assert 1 == 2"}])
        msgs = ctx.build_messages("fix the test", [], fb)
        feedback_msg = [m for m in msgs if "test_add failed" in m.content]
        assert len(feedback_msg) > 0


def test_build_messages_with_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        memory.add(MemoryEntry(id="1", category="convention",
                               content="Use pytest for all tests", keywords=["test", "pytest"]))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("write tests", [], None)
        memory_content = [m for m in msgs if "pytest" in m.content and m.role != "user"]
        assert len(memory_content) > 0


def test_system_prompt_contains_essential_parts():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        ctx = ContextManager(ConfigLoader(), memory, workspace=tmpdir)
        msgs = ctx.build_messages("task", [], None)
        system = next(m for m in msgs if m.role == "system")
        assert "coding agent" in system.content.lower()
        assert "tool" in system.content.lower()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_context.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/context.py
import os
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

    def build_messages(self, user_task: str, history: list[Message],
                       feedback: Feedback | None) -> list[Message]:
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_context.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/context.py tests/test_context.py
git commit -m "feat: ContextManager with system prompt, history, feedback, and memory integration"
```

---

### Task 14: Agent 主循环

**文件：**
- 创建：`src/pyharness/loop.py`
- 创建：`tests/test_loop.py`

**消耗：** 所有之前的模块

**接口：**
- 产生：`AgentLoop` 类
  - `__init__(config, llm, parser, guardrail_chain, tools, feedback, memory, context, hitl, workspace)`
  - `run(task: str, on_event: Callable) -> dict`（返回摘要）
  - `stop()`

**产物：** 完整的管道式主循环，整合所有模块

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_loop.py
import tempfile
import os
from pyharness.loop import AgentLoop
from pyharness.config import ConfigLoader
from pyharness.llm import MockProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine


def test_loop_completes_with_stop_action():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        llm = MockProvider(responses=[
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([RuleGuard(config), ScopeGuard(config, tmpdir)])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        result = loop.run("write hello world", on_event=events.append)
        assert result["status"] == "completed"
        assert result["rounds"] == 1


def test_loop_stops_on_max_rounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        config._config["max_rounds"] = 2
        llm = MockProvider(responses=[
            '{"type": "response", "thought": "thinking..."}',
            '{"type": "response", "thought": "still thinking..."}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        result = loop.run("task", on_event=events.append)
        assert result["status"] == "max_rounds"
        assert result["rounds"] == 2


def test_loop_manual_stop():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        config._config["max_rounds"] = 10
        llm = MockProvider(responses=[
            '{"type": "response", "thought": "thinking..."}',
        ] * 10)
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []

        import threading
        def stop_after_delay():
            import time
            time.sleep(0.05)
            loop.stop()

        threading.Thread(target=stop_after_delay).start()
        result = loop.run("task", on_event=events.append)
        assert result["status"] == "stopped"


def test_loop_events_include_log_messages():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigLoader()
        config.load()
        llm = MockProvider(responses=[
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        parser = ActionParser()
        guardrail = GuardrailChain([])
        tools = ToolExecutor(config, workspace=tmpdir)
        feedback = FeedbackCollector(config)
        memory = MemoryStore(os.path.join(tmpdir, "memory"))
        context = ContextManager(config, memory, workspace=tmpdir)
        hitl = HITLEngine()

        loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, tmpdir)
        events = []
        loop.run("task", on_event=events.append)
        assert len(events) > 0
        assert any("started" in str(e).lower() for e in events)
        assert any("completed" in str(e).lower() for e in events)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_loop.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/loop.py
import threading
from pyharness.models import Message, Action, AgentState
from pyharness.config import ConfigLoader
from pyharness.llm import LLMProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine


class AgentLoop:
    def __init__(self, config: ConfigLoader, llm: LLMProvider, parser: ActionParser,
                 guardrail: GuardrailChain, tools: ToolExecutor, feedback: FeedbackCollector,
                 memory: MemoryStore, context: ContextManager, hitl: HITLEngine,
                 workspace: str):
        self._config = config
        self._llm = llm
        self._parser = parser
        self._guardrail = guardrail
        self._tools = tools
        self._feedback = feedback
        self._memory = memory
        self._context = context
        self._hitl = hitl
        self._workspace = workspace
        self._stop_flag = threading.Event()
        self._history: list[Message] = []
        self._feedbacks: list = []
        self._state = AgentState()

    def run(self, task: str, on_event: callable) -> dict:
        self._stop_flag.clear()
        self._history = []
        self._feedbacks = []
        self._state = AgentState()
        max_rounds = self._config.get("max_rounds", 10)

        on_event({"type": "status", "status": "started", "task": task, "max_rounds": max_rounds})

        for round_num in range(1, max_rounds + 1):
            if self._stop_flag.is_set():
                on_event({"type": "status", "status": "stopped", "round": round_num})
                return {"status": "stopped", "rounds": round_num}

            self._state.current_round = round_num
            self._state.status = "THINKING"
            on_event({"type": "round", "round": round_num, "status": "thinking"})

            last_feedback = self._feedbacks[-1] if self._feedbacks else None
            messages = self._context.build_messages(task, self._history, last_feedback)

            raw_response = self._llm.chat(messages)
            on_event({"type": "llm_response", "content": raw_response[:500]})

            action = self._parser.parse(raw_response)
            self._history.append(Message(role="assistant", content=raw_response))

            on_event({"type": "action", "action_type": action.type,
                      "tool_name": action.tool_name,
                      "thought": action.thought[:200]})

            if action.type == "stop":
                on_event({"type": "status", "status": "completed",
                          "round": round_num, "reason": action.stop_reason})
                return {"status": "completed", "rounds": round_num,
                        "reason": action.stop_reason}

            if action.type == "response":
                continue

            if action.type == "tool_call":
                guard_result = self._guardrail.check(action)
                on_event({"type": "guardrail", "result": {
                    "blocked": guard_result.blocked,
                    "needs_approval": guard_result.needs_approval,
                    "reason": guard_result.reason,
                    "guard_name": guard_result.guard_name,
                }})

                if guard_result.blocked:
                    self._state.guardrail_blocks += 1
                    self._history.append(Message(
                        role="tool",
                        content=f"Action blocked: {guard_result.reason}",
                    ))
                    continue

                if guard_result.needs_approval:
                    self._state.status = "AWAITING_APPROVAL"
                    self._state.pending_approval = action
                    approval_id = self._hitl.request_approval(action)
                    on_event({"type": "approval_required", "approval_id": approval_id,
                              "action": {"tool_name": action.tool_name,
                                         "tool_args": action.tool_args}})

                    decision = self._hitl.wait_for_decision(approval_id)
                    self._state.pending_approval = None
                    on_event({"type": "approval_result", "decision": decision})

                    if decision == "rejected":
                        self._history.append(Message(
                            role="tool",
                            content=f"Action rejected by user: {action.tool_name}",
                        ))
                        continue
                    if decision == "timeout":
                        self._history.append(Message(
                            role="tool",
                            content=f"Action approval timed out: {action.tool_name}",
                        ))
                        continue

                self._state.status = "EXECUTING"
                on_event({"type": "executing", "tool_name": action.tool_name})
                result = self._tools.execute(action)
                on_event({"type": "tool_result", "success": result.success,
                          "output": result.output[:500]})

                fb = self._feedback.collect(result, round_num)
                self._feedbacks.append(fb)
                on_event({"type": "feedback", "status": fb.status, "summary": fb.summary[:200]})

                self._history.append(Message(
                    role="tool",
                    content=f"Tool: {action.tool_name}\nResult: {result.output[:1000]}\nError: {result.error or ''}",
                ))

                if self._feedback.is_stuck(self._feedbacks):
                    on_event({"type": "status", "status": "stuck", "round": round_num})
                    return {"status": "stuck", "rounds": round_num}

        on_event({"type": "status", "status": "max_rounds", "round": max_rounds})
        return {"status": "max_rounds", "rounds": max_rounds}

    def stop(self):
        self._stop_flag.set()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_loop.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/loop.py tests/test_loop.py
git commit -m "feat: Agent main loop with full pipeline (context→LLM→parse→guard→execute→feedback)"
```

---

### Task 15: 凭据管理

**文件：**
- 创建：`src/pyharness/credential.py`
- 创建：`tests/test_credential.py`

**消耗：** 独立模块

**接口：**
- 产生：`CredentialManager` 类
  - `__init__(service_name: str = "pyharness")`
  - `is_set() -> bool`
  - `get() -> str | None`
  - `set(key: str)`
  - `update(key: str)`
  - `clear()`

**产物：** OS keyring 优先 + 加密文件备选的凭据管理

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_credential.py
import os
import tempfile
from unittest.mock import patch, MagicMock
from pyharness.credential import CredentialManager


def test_credential_is_set_returns_false_when_empty():
    with patch("keyring.get_password", return_value=None):
        manager = CredentialManager(service_name="test_harness")
        assert manager.is_set() is False


def test_credential_is_set_returns_true_when_exists():
    with patch("keyring.get_password", return_value="sk-test-key"):
        manager = CredentialManager(service_name="test_harness")
        assert manager.is_set() is True


def test_credential_get_returns_key():
    with patch("keyring.get_password", return_value="sk-test-key"):
        manager = CredentialManager(service_name="test_harness")
        assert manager.get() == "sk-test-key"


def test_credential_set_stores_key():
    with patch("keyring.set_password") as mock_set:
        manager = CredentialManager(service_name="test_harness")
        manager.set("sk-new-key")
        mock_set.assert_called_once_with("test_harness", "api_key", "sk-new-key")


def test_credential_clear_removes_key():
    with patch("keyring.delete_password") as mock_delete:
        manager = CredentialManager(service_name="test_harness")
        manager.clear()
        mock_delete.assert_called_once_with("test_harness", "api_key")


def test_credential_get_returns_none_on_error():
    with patch("keyring.get_password", side_effect=Exception("keyring error")):
        manager = CredentialManager(service_name="test_harness")
        assert manager.get() is None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_credential.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/credential.py
import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet


class CredentialManager:
    def __init__(self, service_name: str = "pyharness"):
        self._service_name = service_name
        self._username = "api_key"

    def is_set(self) -> bool:
        return self.get() is not None

    def get(self) -> str | None:
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

    def _get_from_encrypted_file(self) -> str | None:
        enc_path = self._encrypted_file_path()
        if not os.path.exists(enc_path):
            return None
        try:
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
        key = self._derive_key()
        f = Fernet(key)
        encrypted = f.encrypt(api_key.encode()).decode()
        with open(enc_path, "w") as fp:
            json.dump({"encrypted": encrypted}, fp)

    def _derive_key(self) -> bytes:
        machine_id = hashlib.sha256(os.environ.get("COMPUTERNAME", "pyharness").encode()).digest()
        return base64.urlsafe_b64encode(machine_id)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_credential.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/credential.py tests/test_credential.py
git commit -m "feat: CredentialManager with OS keyring + encrypted file fallback"
```

---

### Task 16: WebUI 后端（FastAPI + WebSocket）

**文件：**
- 创建：`src/pyharness/webui/server.py`
- 创建：`src/pyharness/main.py`

**消耗：** 所有之前的模块，特别是 `loop.py`

**接口：**
- 产生：FastAPI 应用
  - `POST /api/chat` — 提交任务，启动 agent
  - `POST /api/approve` — 审批操作
  - `GET /api/status` — 查询状态
  - `WebSocket /ws` — 实时推送事件

**产物：** 可通过 HTTP API 和 WebSocket 交互的 Web 服务

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_webui.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_webui.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 编写实现**

```python
# src/pyharness/webui/server.py
import json
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pyharness.config import ConfigLoader
from pyharness.llm import AnthropicProvider, MockProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine
from pyharness.loop import AgentLoop
from pyharness.credential import CredentialManager
import os


class ChatRequest(BaseModel):
    task: str


class ApproveRequest(BaseModel):
    approval_id: str
    decision: str  # "approve" or "reject"


class AppState:
    def __init__(self):
        self.loop: AgentLoop | None = None
        self.hitl: HITLEngine | None = None
        self.config: ConfigLoader | None = None
        self.credential: CredentialManager | None = None
        self.websocket: WebSocket | None = None
        self.running = False

    def status(self) -> dict:
        if self.running and self.loop:
            return {
                "status": self.loop._state.status.lower(),
                "current_round": self.loop._state.current_round,
                "max_rounds": self.loop._state.max_rounds,
                "guardrail_blocks": self.loop._state.guardrail_blocks,
            }
        return {"status": "idle"}


state = AppState()


def create_app(config: ConfigLoader = None) -> FastAPI:
    if config is None:
        config = ConfigLoader()
        config.load()
    state.config = config
    state.credential = CredentialManager()

    app = FastAPI(title="PyHarness")

    @app.get("/api/status")
    async def get_status():
        return state.status()

    @app.post("/api/chat")
    async def chat(request: ChatRequest):
        if state.running:
            return {"error": "Agent is already running"}, 409
        threading.Thread(target=_run_agent, args=(request.task,), daemon=True).start()
        return {"status": "started", "task": request.task}

    @app.post("/api/approve")
    async def approve(request: ApproveRequest):
        if not state.hitl:
            return {"error": "No HITL engine"}, 404
        if request.decision == "approve":
            state.hitl.approve(request.approval_id)
        elif request.decision == "reject":
            state.hitl.reject(request.approval_id)
        return {"status": "ok"}

    @app.post("/api/stop")
    async def stop():
        if state.loop:
            state.loop.stop()
        return {"status": "stopping"}

    @app.get("/api/credential/status")
    async def credential_status():
        return {"configured": state.credential.is_set()}

    @app.post("/api/credential/set")
    async def credential_set(data: dict):
        state.credential.set(data["key"])
        return {"status": "ok"}

    @app.post("/api/credential/clear")
    async def credential_clear():
        state.credential.clear()
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        state.websocket = ws
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            state.websocket = None

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index():
        index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "PyHarness WebUI"}

    return app


def _run_agent(task: str):
    config = state.config
    workspace = os.getcwd()

    memory = MemoryStore(os.path.join(workspace, ".harness", "memory"))
    context = ContextManager(config, memory, workspace)
    hitl = HITLEngine(timeout=config.get("approval_timeout", 120))
    state.hitl = hitl

    guardrail = GuardrailChain([
        RuleGuard(config),
        ScopeGuard(config, workspace),
        ApprovalGuard(config),
    ])

    api_key = state.credential.get()
    if api_key and not config.get("use_mock", False):
        try:
            llm = AnthropicProvider(api_key=api_key, model=config.get("model", "claude-sonnet-4-20250514"))
        except Exception:
            llm = MockProvider(responses=[
                '{"type": "stop", "stop_reason": "error", "thought": "LLM connection failed"}'
            ])
    else:
        llm = MockProvider(responses=[
            '{"type": "stop", "stop_reason": "no_api_key", "thought": "please configure API key"}'
        ])

    parser = ActionParser()
    tools = ToolExecutor(config, workspace)
    feedback = FeedbackCollector(config)

    loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, workspace)
    state.loop = loop
    state.running = True

    async def send_event(event):
        if state.websocket:
            try:
                await state.websocket.send_text(json.dumps(event, default=str))
            except Exception:
                pass

    def on_event(event):
        if state.websocket:
            try:
                asyncio.run_coroutine_threadsafe(
                    state.websocket.send_text(json.dumps(event, default=str)),
                    asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else None
                )
            except Exception:
                pass

    try:
        result = loop.run(task, on_event=on_event)
        on_event({"type": "done", "result": result})
    except Exception as e:
        on_event({"type": "error", "error": str(e)})
    finally:
        state.running = False
        state.hitl = None
```

```python
# src/pyharness/main.py
import uvicorn
from pyharness.webui.server import create_app


def main():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_webui.py -v
```

预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/pyharness/webui/server.py src/pyharness/main.py tests/test_webui.py
git commit -m "feat: FastAPI + WebSocket backend with chat, approve, status endpoints"
```

---

### Task 17: WebUI 前端

**文件：**
- 创建：`src/pyharness/webui/static/index.html`
- 创建：`src/pyharness/webui/static/style.css`
- 创建：`src/pyharness/webui/static/app.js`

**消耗：** WebUI 后端的 API 和 WebSocket

**产物：** 三栏式类终端 Web 界面

- [ ] **Step 1: 编写 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PyHarness - Coding Agent</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div class="panel-header">文件树</div>
    <div id="file-tree">加载中...</div>
  </div>
  <div id="main">
    <div id="terminal">
      <div id="terminal-output"></div>
      <div id="approval-box" class="hidden">
        <div class="approval-header">需要审批</div>
        <div id="approval-content"></div>
        <div class="approval-actions">
          <button onclick="handleApproval('approve')" class="btn-approve">通过</button>
          <button onclick="handleApproval('reject')" class="btn-reject">拒绝</button>
        </div>
      </div>
      <div id="input-line">
        <span class="prompt">$</span>
        <input type="text" id="user-input" placeholder="输入任务..." autofocus>
        <button onclick="sendTask()" class="btn-send">发送</button>
      </div>
    </div>
  </div>
  <div id="status-panel">
    <div class="panel-header">状态</div>
    <div class="status-item"><span class="label">状态:</span> <span id="agent-status">空闲</span></div>
    <div class="status-item"><span class="label">轮次:</span> <span id="agent-round">0/0</span></div>
    <div class="status-item"><span class="label">护栏拦截:</span> <span id="guard-blocks">0</span></div>
    <div class="status-item"><span class="label">API Key:</span> <span id="key-status">检查中...</span></div>
  </div>
</div>
<div id="bottom-bar">
  <button onclick="showConfig()">配置</button>
  <button onclick="showGuardLog()">护栏日志</button>
  <button onclick="stopAgent()">停止</button>
</div>
<div id="setup-modal" class="modal hidden">
  <div class="modal-content">
    <h3>配置 API Key</h3>
    <p>请输入你的 Anthropic API Key（不会存储到日志或Git）：</p>
    <input type="password" id="api-key-input" placeholder="sk-ant-...">
    <div class="modal-actions">
      <button onclick="saveApiKey()">保存</button>
      <button onclick="closeSetup()">跳过</button>
    </div>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 编写 style.css**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Consolas', 'Courier New', monospace; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
#app { display: flex; flex: 1; overflow: hidden; }
#sidebar { width: 220px; border-right: 1px solid #333; overflow-y: auto; padding: 8px; background: #16213e; }
#main { flex: 1; display: flex; flex-direction: column; }
#terminal { flex: 1; display: flex; flex-direction: column; background: #0d1117; padding: 8px; overflow: hidden; }
#terminal-output { flex: 1; overflow-y: auto; padding: 4px; white-space: pre-wrap; word-break: break-all; font-size: 13px; line-height: 1.5; }
#status-panel { width: 200px; border-left: 1px solid #333; padding: 8px; background: #16213e; }
.panel-header { font-weight: bold; font-size: 13px; padding: 4px 0; border-bottom: 1px solid #333; margin-bottom: 8px; color: #58a6ff; }
.status-item { font-size: 12px; padding: 4px 0; }
.status-item .label { color: #8b949e; }
#input-line { display: flex; padding: 8px 0; border-top: 1px solid #333; }
.prompt { color: #3fb950; margin-right: 8px; }
#user-input { flex: 1; background: transparent; border: none; color: #e0e0e0; font-family: inherit; font-size: 13px; outline: none; }
.btn-send { background: #238636; color: white; border: none; padding: 4px 12px; cursor: pointer; border-radius: 4px; }
#approval-box { background: #292929; border: 1px solid #d29922; border-radius: 6px; padding: 12px; margin: 8px 0; }
#approval-box.hidden { display: none; }
.approval-header { color: #d29922; font-weight: bold; margin-bottom: 8px; }
.approval-actions { margin-top: 8px; display: flex; gap: 8px; }
.btn-approve { background: #238636; color: white; border: none; padding: 6px 16px; cursor: pointer; border-radius: 4px; }
.btn-reject { background: #da3633; color: white; border: none; padding: 6px 16px; cursor: pointer; border-radius: 4px; }
#bottom-bar { display: flex; gap: 8px; padding: 6px 12px; background: #0d1117; border-top: 1px solid #333; }
#bottom-bar button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
#bottom-bar button:hover { background: #30363d; }
.modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; }
.modal.hidden { display: none; }
.modal-content { background: #1a1a2e; padding: 24px; border-radius: 8px; max-width: 400px; width: 100%; }
.modal-content h3 { margin-bottom: 12px; color: #58a6ff; }
.modal-content p { margin-bottom: 12px; font-size: 13px; color: #8b949e; }
.modal-content input { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #30363d; color: #e0e0e0; border-radius: 4px; margin-bottom: 12px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.modal-actions button { padding: 6px 16px; border-radius: 4px; border: none; cursor: pointer; }
.modal-actions button:first-child { background: #238636; color: white; }
.modal-actions button:last-child { background: #21262d; color: #c9d1d9; }
.log-user { color: #3fb950; }
.log-agent { color: #e0e0e0; }
.log-system { color: #8b949e; }
.log-guard { color: #f85149; }
.log-approval { color: #d29922; }
.log-feedback { color: #58a6ff; }
</style>
```

- [ ] **Step 3: 编写 app.js**

```javascript
let ws;
let pendingApprovalId = null;

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws`);
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    handleEvent(event);
  };
  ws.onclose = () => setTimeout(connect, 2000);
}

function handleEvent(event) {
  const out = document.getElementById('terminal-output');
  const div = document.createElement('div');
  switch (event.type) {
    case 'status':
      div.className = 'log-system';
      div.textContent = `[系统] ${event.status}: ${event.task || ''} (最大轮次: ${event.max_rounds || ''})`;
      document.getElementById('agent-status').textContent = event.status;
      document.getElementById('agent-round').textContent = `${event.round || 0}/${event.max_rounds || 0}`;
      break;
    case 'llm_response':
      div.className = 'log-agent';
      div.textContent = `[agent] ${event.content}`;
      break;
    case 'action':
      div.className = 'log-agent';
      div.textContent = `[agent] 动作: ${event.action_type} ${event.tool_name || ''}`;
      break;
    case 'guardrail':
      const gr = event.result;
      div.className = gr.blocked ? 'log-guard' : (gr.needs_approval ? 'log-approval' : 'log-system');
      if (gr.blocked) {
        div.textContent = `[护栏] 拦截: ${gr.reason} (${gr.guard_name})`;
        document.getElementById('guard-blocks').textContent = parseInt(document.getElementById('guard-blocks').textContent) + 1;
      } else if (gr.needs_approval) {
        div.textContent = `[护栏] 需要审批: ${gr.reason}`;
      }
      break;
    case 'approval_required':
      pendingApprovalId = event.approval_id;
      document.getElementById('approval-content').textContent =
        `操作: ${event.action.tool_name} ${JSON.stringify(event.action.tool_args)}`;
      document.getElementById('approval-box').classList.remove('hidden');
      div.className = 'log-approval';
      div.textContent = `[审批] 等待审批: ${event.action.tool_name}`;
      break;
    case 'approval_result':
      div.className = 'log-system';
      div.textContent = `[审批] 结果: ${event.decision}`;
      document.getElementById('approval-box').classList.add('hidden');
      pendingApprovalId = null;
      break;
    case 'executing':
      div.className = 'log-agent';
      div.textContent = `[agent] 执行: ${event.tool_name}`;
      break;
    case 'tool_result':
      div.className = event.success ? 'log-agent' : 'log-feedback';
      div.textContent = `[结果] ${event.success ? '成功' : '失败'}: ${event.output?.substring(0, 200) || ''}`;
      break;
    case 'feedback':
      div.className = event.status === 'PASS' ? 'log-agent' : 'log-feedback';
      div.textContent = `[反馈] ${event.status}: ${event.summary}`;
      break;
    case 'done':
      div.className = 'log-system';
      div.textContent = `[完成] ${JSON.stringify(event.result)}`;
      document.getElementById('agent-status').textContent = '空闲';
      break;
    case 'error':
      div.className = 'log-guard';
      div.textContent = `[错误] ${event.error}`;
      break;
    case 'round':
      document.getElementById('agent-round').textContent = `${event.round}/0`;
      break;
    default:
      div.className = 'log-system';
      div.textContent = JSON.stringify(event);
  }
  out.appendChild(div);
  out.scrollTop = out.scrollHeight;
}

function sendTask() {
  const input = document.getElementById('user-input');
  const task = input.value.trim();
  if (!task) return;
  const out = document.getElementById('terminal-output');
  const div = document.createElement('div');
  div.className = 'log-user';
  div.textContent = `$ ${task}`;
  out.appendChild(div);
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task }),
  });
  input.value = '';
}

function handleApproval(decision) {
  if (!pendingApprovalId) return;
  fetch('/api/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approval_id: pendingApprovalId, decision }),
  });
  document.getElementById('approval-box').classList.add('hidden');
}

function stopAgent() {
  fetch('/api/stop', { method: 'POST' });
}

async function checkKeyStatus() {
  const resp = await fetch('/api/credential/status');
  const data = await resp.json();
  document.getElementById('key-status').textContent = data.configured ? '已配置' : '未配置';
  if (!data.configured) {
    document.getElementById('setup-modal').classList.remove('hidden');
  }
}

async function saveApiKey() {
  const key = document.getElementById('api-key-input').value.trim();
  if (!key) return;
  await fetch('/api/credential/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  document.getElementById('setup-modal').classList.add('hidden');
  document.getElementById('key-status').textContent = '已配置';
}

function closeSetup() {
  document.getElementById('setup-modal').classList.add('hidden');
}

function showConfig() { alert('配置文件: .harness/config.yaml'); }
function showGuardLog() { alert('护栏日志查看（待实现）'); }

document.getElementById('user-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendTask();
});

connect();
checkKeyStatus();
```

- [ ] **Step 4: 提交**

```bash
git add src/pyharness/webui/static/
git commit -m "feat: WebUI frontend with terminal-style layout, WebSocket events, and approval UI"
```

---

### Task 18: Docker 分发

**文件：**
- 创建：`Dockerfile`
- 创建：`.dockerignore`

**产物：** 可一键构建和运行的 Docker 镜像

- [ ] **Step 1: 编写 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" && pip install --no-cache-dir cryptography

COPY src/ src/

RUN mkdir -p .harness/memory

EXPOSE 8080

CMD ["python", "-m", "pyharness.main"]
```

- [ ] **Step 2: 编写 .dockerignore**

```
__pycache__/
*.pyc
*.pyo
.env
.harness/key.enc
*.key
*.pem
.git/
.gitignore
tests/
dist/
build/
*.egg-info/
.venv/
venv/
```

- [ ] **Step 3: 提交**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: Dockerfile and .dockerignore for containerized distribution"
```

---

### Task 19: CI 配置

**文件：**
- 创建：`.gitlab-ci.yml`

**产物：** 包含 `unit-test` job 的 CI 配置

- [ ] **Step 1: 编写 .gitlab-ci.yml**

```yaml
stages:
  - test
  - build

unit-test:
  stage: test
  image: python:3.12-slim
  before_script:
    - pip install -e ".[dev]"
    - pip install cryptography
  script:
    - pytest tests/ -v --tb=short
  artifacts:
    when: always
    paths:
      - .pytest_cache/
    expire_in: 7 days

docker-build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t pyharness:latest .
  only:
    - main
```

- [ ] **Step 2: 提交**

```bash
git add .gitlab-ci.yml
git commit -m "feat: CI configuration with unit-test and docker-build jobs"
```

---

### Task 20: 机制演示测试

**文件：**
- 创建：`tests/test_demo.py`

**消耗：** 所有核心模块

**产物：** 三个确定性机制演示场景

- [ ] **Step 1: 编写机制演示测试**

```python
# tests/test_demo.py
import os
import tempfile
import threading
from pyharness.loop import AgentLoop
from pyharness.config import ConfigLoader
from pyharness.llm import MockProvider
from pyharness.parser import ActionParser
from pyharness.guardrail.chain import GuardrailChain
from pyharness.guardrail.rule_guard import RuleGuard
from pyharness.guardrail.scope_guard import ScopeGuard
from pyharness.guardrail.approval_guard import ApprovalGuard
from pyharness.tools import ToolExecutor
from pyharness.feedback import FeedbackCollector
from pyharness.memory import MemoryStore
from pyharness.context import ContextManager
from pyharness.hitl import HITLEngine


def build_harness(workspace, llm_responses, max_rounds=10):
    config = ConfigLoader()
    config.load()
    config._config["max_rounds"] = max_rounds
    config._config["tools"]["enabled"] = ["read_file", "write_file", "execute_shell",
                                           "run_tests", "run_lint", "list_files"]
    llm = MockProvider(responses=llm_responses)
    parser = ActionParser()
    guardrail = GuardrailChain([
        RuleGuard(config),
        ScopeGuard(config, workspace),
        ApprovalGuard(config),
    ])
    tools = ToolExecutor(config, workspace=workspace)
    feedback = FeedbackCollector(config)
    memory = MemoryStore(os.path.join(workspace, ".harness", "memory"))
    context = ContextManager(config, memory, workspace=workspace)
    hitl = HITLEngine(timeout=30)
    loop = AgentLoop(config, llm, parser, guardrail, tools, feedback, memory, context, hitl, workspace)
    return loop, hitl


def test_demo_1_guardrail_blocks_dangerous_action():
    """演示 1: 治理护栏拦截危险动作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loop, hitl = build_harness(tmpdir, llm_responses=[
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "rm -rf /"}, "thought": "cleaning up"}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        events = []
        result = loop.run("delete everything", on_event=events.append)

        guard_events = [e for e in events if e.get("type") == "guardrail"]
        assert len(guard_events) > 0
        assert guard_events[0]["result"]["blocked"] is True
        assert guard_events[0]["result"]["guard_name"] == "RuleGuard"


def test_demo_2_feedback_loop_changes_behavior():
    """演示 2: 注入失败，反馈闭环使 agent 收到反馈并改变下一步动作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_calc.py")
        with open(test_file, "w") as f:
            f.write("def test_add():\n    assert 1 + 1 == 3\n")

        loop, hitl = build_harness(tmpdir, llm_responses=[
            '{"type": "tool_call", "tool_name": "run_tests", "tool_args": {"command": "pytest test_calc.py"}, "thought": "running tests"}',
            '{"type": "tool_call", "tool_name": "write_file", "tool_args": {"path": "' + test_file.replace('\\', '\\\\') + '", "content": "def test_add():\\n    assert 1 + 1 == 2\\n"}, "thought": "fixing the test based on feedback"}',
            '{"type": "tool_call", "tool_name": "run_tests", "tool_args": {"command": "pytest test_calc.py"}, "thought": "re-running tests after fix"}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "tests pass now"}',
        ])
        events = []
        result = loop.run("fix the failing test", on_event=events.append)

        feedback_events = [e for e in events if e.get("type") == "feedback"]
        assert len(feedback_events) >= 2

        first_feedback = feedback_events[0]
        assert first_feedback["status"] == "FAIL"

        last_feedback = feedback_events[-1]
        assert last_feedback["status"] == "PASS"

        actions = [e for e in events if e.get("type") == "action"]
        assert any("write_file" in str(e.get("tool_name", "")) for e in actions)
        assert any("fix" in str(e.get("thought", "")).lower() for e in actions)


def test_demo_3_hitl_approval_with_timeout_reject():
    """演示 3: HITL 审批超时默认拒绝（重点维度：护栏）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loop, hitl = build_harness(tmpdir, llm_responses=[
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "pip install requests"}, "thought": "installing dependency"}',
            '{"type": "tool_call", "tool_name": "execute_shell", "tool_args": {"command": "pytest"}, "thought": "running tests without the dependency"}',
            '{"type": "stop", "stop_reason": "task_complete", "thought": "done"}',
        ])
        events = []
        result = loop.run("install requests", on_event=events.append)

        approval_events = [e for e in events if e.get("type") == "approval_required"]
        assert len(approval_events) > 0
        assert approval_events[0]["action"]["tool_name"] == "execute_shell"

        timeouts = [e for e in events if e.get("type") == "approval_result" and e.get("decision") == "timeout"]
        assert len(timeouts) > 0
```

- [ ] **Step 2: 运行测试验证通过**

```bash
pytest tests/test_demo.py -v
```

预期：全部 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/test_demo.py
git commit -m "feat: mechanism demo tests (guardrail block, feedback loop, HITL timeout)"
```

---

### Task 21: README

**文件：**
- 创建：`README.md`

**产物：** 完整的项目文档

- [ ] **Step 1: 编写 README.md**

内容必须包含：项目简介、安装、运行、分发命令、目录结构、安全边界说明。

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: README with install, usage, Docker, and security instructions"
```

---

## 并行机会

以下 Task 组可以并行执行（使用 worktree）：

| 并行组 | Tasks |
|--------|-------|
| 核心模块 | Task 4 (LLM) + Task 5 (Parser) + Task 6 (Tools) |
| 反馈+记忆 | Task 11 (Feedback) + Task 12 (Memory) |
| 交付 | Task 18 (Docker) + Task 19 (CI) + Task 20 (Demo) + Task 21 (README) |