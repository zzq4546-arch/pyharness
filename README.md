# PyHarness — Coding Agent Harness

> AI4SE 期末项目 · A · Coding Agent Harness

PyHarness 是一个 Python 实现的 Coding Agent Harness。它将 LLM 封装为能自主完成编程任务的系统，提供主循环、工具分发、三层治理护栏、HITL 审批、反馈闭环、记忆和配置六大机制。

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd pyharness

# 2. 安装依赖（需要 Python 3.12+）
pip install -e ".[dev]"

# 3. 运行
python -m pyharness.main
# 访问 http://localhost:8080
```

## Docker 运行

```bash
docker build -t pyharness .
docker run -p 8080:8080 pyharness
```

## API Key 配置

首次打开 WebUI 会自动弹出配置向导，输入你的 Anthropic API Key 即可。

Key 的存储方式：
- **优先**：操作系统钥匙串（Windows Credential Manager / macOS Keychain / Linux libsecret）
- **备选**：加密文件 `~/.harness/key.enc`

Key 绝不硬编码在源码中，绝不提交到 Git，绝不写入日志。

## 运行测试

```bash
pytest tests/ -v
```

## 目录结构

```
pyharness/
├── src/pyharness/
│   ├── main.py              # 入口
│   ├── models.py            # 数据模型
│   ├── config.py            # 配置加载
│   ├── context.py           # 上下文管理
│   ├── llm.py               # LLM 抽象层
│   ├── parser.py            # 动作解析
│   ├── guardrail/           # 护栏（重点维度）
│   │   ├── base.py          # 护栏基类
│   │   ├── chain.py         # 护栏链
│   │   ├── rule_guard.py    # 规则护栏
│   │   ├── scope_guard.py   # 范围护栏
│   │   └── approval_guard.py# 审批护栏
│   ├── hitl.py              # HITL 状态机
│   ├── tools.py             # 工具执行器
│   ├── feedback.py          # 反馈收集
│   ├── memory.py            # 记忆存储
│   ├── loop.py              # Agent 主循环
│   ├── credential.py        # 凭据管理
│   └── webui/               # Web 界面
│       ├── server.py        # FastAPI 后端
│       └── static/          # 前端文件
├── tests/
│   ├── test_demo.py         # 机制演示
│   └── ...
├── Dockerfile
├── .gitlab-ci.yml
├── SPEC.md
├── PLAN.md
└── README.md
```

## 安全边界

- API Key 存储在 OS 钥匙串或加密文件中，不落明文
- 三层护栏防止危险命令执行：RuleGuard（命令黑名单）、ScopeGuard（工作区边界）、ApprovalGuard（HITL 审批）
- 审批超时默认拒绝，安全优先
- `.env` 等敏感文件受 ScopeGuard 保护，禁止读写

## 已知限制

- 仅测试 Linux/amd64 平台
- 容器内文件操作受限于挂载的工作目录
- OS keyring 在某些容器环境可能不可用，需回退到加密文件

## 技术栈

- Python 3.12+
- FastAPI + WebSocket
- Anthropic Claude API
- Docker
- pytest