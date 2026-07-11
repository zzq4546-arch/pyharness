# PyHarness — SPEC

> AI4SE 期末项目 · A · Coding Agent Harness

---

## 一、问题陈述

### 要解决的问题

当前 LLM 能力已足够完成大部分编码任务，但将 LLM 从"能写代码"变为"能稳定可靠地完成工程任务"，需要一层工程基础设施——即 harness。PyHarness 是一个 Coding Agent Harness：它封装 LLM 调用，提供主循环、工具分发、治理护栏、反馈闭环、记忆和配置六大机制，将 LLM 转化为一台能自主完成编程任务的系统。

### 目标用户

- 希望用 AI 辅助日常编码的开发者
- 希望理解 agent 内部机制的 AI4SE 学习者
- 需要一个可审计、可安全使用的 coding agent 的团队

### 为什么值得做

现有 coding agent（Claude Code、OpenCode 等）功能强大，但内部机制对用户不透明。PyHarness 将 harness 的每一层工程暴露出来，用户可以看到护栏如何拦截、反馈如何驱动修正、记忆如何组织。它既是实用工具，也是学习 agentic SE 的教具。



## 二、用户故事

| # | 用户故事 | 验收标准 |
|---|---------|---------|
| US1 | 作为开发者，我可以输入一个编程任务，让 agent 自主完成代码编写、测试和修正 | 给定一个简单任务（如"写一个计算器"），agent 能自主完成编码→测试→修正的完整闭环 |
| US2 | 作为开发者，当 agent 尝试执行危险命令时，系统应自动拦截并通知我 | 危险命令（如 `rm -rf /`）被护栏拦截，WebUI 显示拦截信息 |
| US3 | 作为开发者，我可以在 WebUI 中实时看到 agent 的执行过程，并在需要时审批或拒绝其操作 | WebUI 实时推送日志，审批请求内联展示，可点击通过/拒绝 |
| US4 | 作为开发者，我的 API Key 不会被硬编码、不会泄露到 Git 或日志中 | Key 存储在 OS 钥匙串中，日志中不出现明文 key |
| US5 | 作为开发者，我可以通过 Docker 一键启动 PyHarness，并在任意机器上安全配置自己的 key | `docker build && docker run` 后，通过 WebUI 配置向导完成 key 设置 |
| US6 | 作为开发者，当 agent 因测试失败进入自我修正循环时，我能看到反馈如何驱动它的下一步动作 | 反馈模块将测试失败信息回灌给 LLM，agent 据此修改代码，WebUI 显示完整链路 |
| US7 | 作为学习者，我可以在 mock LLM 模式下确定性地验证护栏、反馈等机制的行为 | 运行 `pytest tests/test_demo.py` 即可验证机制演示的三个场景 |

---

## 三、功能规约

### 3.1 Agent 主循环（loop.py）

```
输入：用户任务（自然语言）
行为：
  1. 上下文组装（ContextManager）
  2. 调用 LLM（LLM Abstraction）
  3. 解析动作（ActionParser）
  4. 护栏检查（GuardrailChain）
  5. 如需审批 → HITL 暂停，等待用户决策
  6. 执行工具（ToolExecutor）
  7. 收集反馈（FeedbackCollector）
  8. 回灌到上下文 → 回到步骤 1
  9. 停机判断：任务完成 / 超时 / 卡住 / 手动停止
输出：完成摘要（文件变更列表、测试结果、轮次统计）
```

- 最大轮次：可配置，默认 10
- 连续失败无改善：3 轮，触发卡住停机
- 支持用户通过 WebUI 手动停止

### 3.2 工具分发（tools.py）

| 工具 | 输入 | 行为 | 输出 |
|------|------|------|------|
| `read_file` | 文件路径 | 读取文件内容 | 文件内容字符串 |
| `write_file` | 文件路径 + 内容 | 创建或覆盖文件 | 成功/失败状态 |
| `execute_shell` | 命令字符串 | 执行 shell 命令 | stdout + stderr + 退出码 |
| `run_tests` | 测试命令（可选） | 运行测试套件 | 测试输出 + 通过/失败 |
| `run_lint` | 文件路径（可选） | 运行 lint 检查 | lint 输出 |
| `list_files` | 目录路径 + 模式 | 列出目录结构 | 文件列表 |

- 所有工具输出结构化 JSON
- `execute_shell` 必须通过护栏检查才能执行
- 工具执行有超时限制（可配置，默认 60 秒）

### 3.3 治理护栏（guardrail/）

**RuleGuard（规则护栏）**
- 输入：Action 对象
- 行为：用正则表达式匹配命令黑名单
- 默认黑名单：`rm -rf /`, `sudo`, `chmod 777`, `git push --force`, `DROP TABLE`, `shutdown`, `reboot`, `:(){ :|:& };:` 等
- 规则可通过 `.harness/config.yaml` 自定义
- 输出：`{blocked: bool, reason: str}`

**ScopeGuard（范围护栏）**
- 输入：Action 对象
- 行为：路径规范化 + 前缀检查，确保所有文件操作在项目根目录内
- 防止 `../` 逃逸
- 禁止写入 `.env`、`.git/config`、`*.key`、`*.pem` 等敏感文件
- 输出：`{blocked: bool, reason: str}`

**ApprovalGuard（审批护栏）**
- 输入：Action 对象
- 行为：识别需要人工审批的命令（网络请求、批量删除、Git 历史修改等）
- 触发 HITL 状态机
- 输出：`{needs_approval: bool, reason: str}`

**护栏链执行顺序：** RuleGuard → ScopeGuard → ApprovalGuard
- 任一拦截立即返回，不执行后续护栏
- 被拦截的 action 记录到护栏日志

### 3.4 HITL 审批（hitl.py）

```
状态：IDLE → AWAITING_APPROVAL → APPROVED / REJECTED / TIMEOUT → IDLE
```

- 审批请求通过 WebSocket 推送到 WebUI
- 用户可：通过（继续执行）、拒绝（跳过）、修改（编辑命令后通过）
- 超时默认拒绝（安全优先），超时时间可配置，默认 120 秒
- 拒绝后，拒绝信息回灌到 LLM 上下文

### 3.5 反馈闭环（feedback.py）

- 输入：工具执行结果（结构化 JSON）
- 行为：
  - 测试结果 → 解析为 PASS / FAIL，提取失败信息
  - Lint 结果 → 解析为 CLEAN / ISSUES，提取错误行号
  - Shell 结果 → 检查退出码
- 格式化反馈信息，注入到下一轮 LLM 上下文
- 连续失败检测：同一类错误出现 3 轮 → 触发卡住停机

### 3.6 上下文管理（context.py）

- 系统提示：固定角色定义（"你是一个 coding agent..."）
- 对话历史：最近 N 轮滑动窗口（N 可配置，默认 20）
- 项目文件树摘要
- 反馈注入：上一轮测试/ lint 结果
- Token 预算控制：按 Anthropic 模型上下文窗口限制裁剪

### 3.7 记忆（memory.py）

- 存储位置：`.harness/memory/` 下 JSON 文件
- 存储内容：项目约定、用户偏好、历史决策、常见错误模式
- 检索方式：启动时加载，按关键词匹配注入上下文
- 写入方式：用户可手动编辑，agent 也可在任务完成后追加

### 3.8 配置（config.py）

- 配置文件：`.harness/config.yaml`
- 配置项：护栏规则、工具白名单、模型选择、token 预算、最大轮次、重试次数、超时时间
- 声明式 YAML，用户可编辑
- 默认配置内置在代码中，`.harness/config.yaml` 可覆盖

### 3.9 LLM 抽象层（llm.py）

- 接口：`LLMProvider` 抽象基类
  - `chat(messages: list[Message]) -> LLMResponse`
- 实现：
  - `AnthropicProvider`：调用 Anthropic API（`claude-sonnet-4-20250514` 等）
  - `MockProvider`：返回预设的响应序列，用于单元测试
- 通过环境变量/配置选择 provider

### 3.10 ActionParser（parser.py）

- 输入：LLM 原始响应文本
- 行为：解析为结构化 Action
  - 优先匹配 `tool_call`（JSON 格式）
  - 其次 `response`（纯文本）
  - 最后 `stop`（任务完成声明）
- 解析失败 → 回退为 `response`，原样输出
- Action 数据结构：
  ```python
  Action:
    type: "tool_call" | "response" | "stop"
    tool_name: str | None
    tool_args: dict | None
    thought: str
    stop_reason: str | None
  ```

### 3.11 凭据管理（credential.py）

- 存储：优先 OS keyring（`keyring` 库），备选加密文件
- 操作：setup（录入）、status（检查是否已配置）、update（更新）、clear（清除）
- 首次运行：检测无 key → 引导用户输入（隐藏回显）
- 查看状态：仅显示 `[已配置]` / `[未配置]`，绝不回显明文
- 支持 `.env` 作为来源但标注风险

### 3.12 WebUI（webui/）

- 三栏布局：文件树 + 终端主区域 + 状态面板
- WebSocket 实时推送：日志行、审批请求、状态变更
- HTTP API：`POST /api/chat`、`POST /api/approve`、`GET /api/status`
- 审批请求内联显示，带通过/拒绝/修改按钮
- 底栏：配置入口、护栏日志、会话历史、停止按钮
- 首次访问弹出 API Key 配置向导

---

## 四、非功能性需求

### 4.1 性能
- Agent 单轮响应时间（不含 LLM 调用）：< 100ms
- WebSocket 推送延迟：< 50ms
- 支持至少 20 轮对话不降级

### 4.2 安全（含凭据威胁模型）

**威胁模型：**
| 威胁 | 对策 |
|------|------|
| API Key 硬编码在源码中 | 代码中不出现任何 key 字符串 |
| API Key 泄露到 Git | `.gitignore` 排除 `.env`、`.harness/key.enc`、`*.key`；提交前检查 |
| API Key 出现在日志/终端输出 | 日志模块过滤 key 模式；key 仅通过隐藏输入获取 |
| 危险命令被执行 | 三层护栏（规则/范围/审批）拦截 |
| 文件越权访问 | ScopeGuard 限制工作目录，禁止路径逃逸 |
| HITL 审批超时 | 默认拒绝，安全优先 |

**凭据存储方案：**
- 优先：OS Keyring（Windows Credential Manager / macOS Keychain / Linux libsecret）
- 备选：AES-256-GCM 加密文件 + PBKDF2 主密码派生密钥
- `.env` 可用但标注明文风险

### 4.3 可用性
- Docker 一键启动
- WebUI 首次访问自动弹出配置向导
- 护栏拦截信息清晰可读，包含原因说明
- 审批请求有超时提示，防止用户困惑

### 4.4 可观测性
- 所有护栏拦截记录到日志
- Agent 每轮执行统计（轮次、token 用量、工具调用次数）
- WebUI 状态面板实时显示运行指标

---

## 五、系统架构

### 5.1 组件图

```
┌─────────────────────────────────────────────────────────┐
│                        WebUI                             │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ 文件树    │  │  终端主区域       │  │  状态面板      │  │
│  │          │  │  (WebSocket 推送) │  │              │  │
│  └──────────┘  └────────┬─────────┘  └───────────────┘  │
│                         │                               │
│              ┌──────────▼──────────┐                    │
│              │   FastAPI + WS      │                    │
│              └──────────┬──────────┘                    │
└─────────────────────────┼───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Agent 主循环 (Pipeline)                 │
│                                                         │
│  ContextMgr ──► LLM ──► Parser ──► GuardrailChain ──►   │
│       ▲                                        │        │
│       │              ┌─────────────────────────┘        │
│       │              ▼                                  │
│       └── Feedback ◄── Tools ◄── HITL ◄── Executor      │
│                                                         │
│  ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ Memory │ │Config│ │Cred  │ │HITL  │ │Stop  │        │
│  │ Store  │ │Loader│ │Mgr   │ │Engine│ │Judge │        │
│  └────────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │            GuardrailChain                 │          │
│  │  RuleGuard → ScopeGuard → ApprovalGuard   │          │
│  └──────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 数据流

```
用户输入(WebUI) → FastAPI → Agent 主循环
  └→ ContextMgr 组装上下文
    └→ LLM 调用 (Anthropic API)
      └→ Parser 解析为 Action
        └→ GuardrailChain 检查
          ├─ 拦截 → 记录日志 → 回灌拦截信息 → 回到 LLM
          ├─ 需审批 → HITL → WebSocket 推送 → 等待用户 → 继续/拒绝
          └─ 放行 → ToolExecutor 执行
            └→ FeedbackCollector 收集结果
              └→ StopJudge 停机判断
                ├─ 继续 → 回灌到 ContextMgr → 下一轮
                └─ 停机 → 输出摘要 → WebSocket 推送完成
```

### 5.3 外部依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| Anthropic API | LLM 调用 | `anthropic` Python SDK |
| `keyring` | 跨平台凭据存储 | 最新稳定版 |
| FastAPI | HTTP + WebSocket 服务 | 最新稳定版 |
| `uvicorn` | ASGI 服务器 | 最新稳定版 |
| `pyyaml` | 配置文件解析 | 最新稳定版 |
| `pytest` | 测试框架 | 最新稳定版 |

---

## 六、数据模型

### 6.1 Message

```python
Message:
  role: "system" | "user" | "assistant" | "tool"
  content: str
  tool_call_id: str | None
  tool_result: str | None
```

### 6.2 Action

```python
Action:
  type: "tool_call" | "response" | "stop"
  tool_name: str | None
  tool_args: dict | None
  thought: str
  stop_reason: str | None
```

### 6.3 GuardResult

```python
GuardResult:
  blocked: bool
  needs_approval: bool
  reason: str
  guard_name: str
```

### 6.4 ToolResult

```python
ToolResult:
  tool_name: str
  success: bool
  output: str
  error: str | None
  exit_code: int | None
```

### 6.5 Feedback

```python
Feedback:
  status: "PASS" | "FAIL" | "ERROR"
  summary: str
  details: list[dict]  # 具体失败信息
  round: int
```

### 6.6 MemoryEntry

```python
MemoryEntry:
  id: str
  category: str         # "convention" | "decision" | "preference" | "error_pattern"
  content: str
  keywords: list[str]
  created_at: datetime
  updated_at: datetime
```

### 6.7 AgentState

```python
AgentState:
  status: "IDLE" | "THINKING" | "AWAITING_APPROVAL" | "EXECUTING" | "STOPPED"
  current_round: int
  max_rounds: int
  tokens_used: int
  guardrail_blocks: int
  pending_approval: Action | None
```

---

## 七、凭据与分发设计

### 7.1 凭据存储

见 §4.2 安全部分和 §3.11 凭据管理模块。

### 7.2 分发

**形态：Docker 容器**

```bash
# 构建
docker build -t pyharness .

# 运行
docker run -p 8080:8080 pyharness
```

**Dockerfile 结构：**
- 基础镜像：`python:3.12-slim`
- 安装依赖 → 复制源码 → 暴露 8080
- 启动命令：`python -m pyharness`
- `.dockerignore`：排除 `.env`、`.git`、`__pycache__`、`*.pyc`

**目标机器上的 key 配置：**
- 方式一：进入容器后通过 WebUI 配置向导（首次访问自动弹出）
- 方式二：挂载宿主 keyring socket（Linux）
- 方式三：挂载加密文件：`docker run -v ~/.harness:/root/.harness ...`

**已知限制：**
- 仅测试 Linux/amd64 平台
- 容器内文件操作受限于挂载的工作目录
- OS keyring 在某些容器环境可能不可用，需回退到加密文件

---

## 八、技术选型与理由

| 选择 | 理由 |
|------|------|
| Python | 开发效率高，LLM 生态成熟（Anthropic SDK），`keyring` 跨平台，`pytest` 测试生态完善 |
| Anthropic Claude | 课程推荐，coding 能力强，API 稳定 |
| FastAPI | 异步支持好，WebSocket 原生支持，轻量 |
| Docker 分发 | 环境一致性好，一键部署，助教评分方便 |
| OS Keyring | 系统原生安全存储，无需额外部署 |
| 无前端框架 | WebUI 简单（类终端），纯 HTML/CSS/JS 足够，避免复杂构建 |
| Open Design | 按课程推荐，用于 WebUI 终端风格组件 |

---

## 九、验收标准

| 功能 | 验收标准 |
|------|---------|
| Agent 主循环 | 给定任务后能自主完成编码→测试→修正闭环，最终测试通过 |
| 护栏拦截 | 危险命令被确定性地拦截，不依赖 LLM 判断 |
| HITL 审批 | 审批请求在 WebUI 显示，用户可通过/拒绝，超时默认拒绝 |
| 反馈闭环 | 测试失败信息回灌后 agent 改变行为，最多 3 轮自我修正 |
| 凭据安全 | Key 不在源码、Git、日志中出现；仅通过 keyring 或加密文件存储 |
| Docker 分发 | `docker build && docker run` 后 WebUI 可访问 |
| Mock LLM 单测 | 移除真实 LLM 后，核心机制（护栏/反馈/HITL/停机）仍可确定性测试 |
| 机制演示 | 运行 `pytest tests/test_demo.py` 确定性地复现三个场景 |
| CI | `.gitlab-ci.yml` 包含 `unit-test` job，最后一次执行 pass |
| WebUI 可访问 | 提供线上部署 URL，WebUI 正常运行 |

---

## 十、领域与机制设计（A.5 额外要求）

### 领域：Coding

**反馈信号：**
- 测试结果（PASS/FAIL）：最核心的客观信号，确定性、可回灌
- Lint/类型检查：代码质量信号
- Shell 退出码：命令执行是否成功

**危险动作：**
- 破坏性 shell 命令：`rm -rf`、`sudo`、`chmod`、格式化磁盘
- 网络操作：`curl`、`pip install`、`git clone`（可能引入恶意代码）
- 批量删除文件
- Git 历史修改：`push --force`、`rebase`
- 文件越权访问：路径逃逸、读取敏感文件（`.env`、密钥）
- 对外发布：`git push`、`docker push`、`npm publish`

**所需工具：**
- 读写文件、执行 shell、运行测试/ lint、列出目录

**记忆需求：**
- 项目约定（代码风格、技术栈）
- 历史决策（为什么这样设计）
- 用户偏好（测试框架、lint 规则）
- 常见错误模式（避免重复犯错）

### 重点维度：治理护栏

**为什么选它：**
1. 天然由代码构成，完全满足 §A.4-C 的判定标准（移除 LLM 后仍可单位测试）
2. 三层护栏设计（RuleGuard → ScopeGuard → ApprovalGuard）有清晰的分层和递进
3. HITL 状态机是经典的工程问题，有足够的设计深度
4. 安全是 coding agent 实际部署中最关键的工程问题

**如何编码实现：**
- RuleGuard：正则表达式引擎，命令黑白名单匹配，代码量不大但设计精良
- ScopeGuard：路径规范化 + 前缀检查 + 敏感文件名单，纯路径运算
- ApprovalGuard：规则匹配 + HITL 状态机触发
- 所有护栏都实现 `Guard` 抽象接口，可组合为拦截器链
- 每个护栏杆都有独立的 mock 单元测试

---

## 十一、风险与未决问题

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 响应格式不稳定，ActionParser 解析失败 | Agent 行为不可预测 | 多层回退策略，解析失败降级为纯文本输出 |
| 护栏规则过于宽松导致危险命令漏过 | 安全风险 | 默认配置保守，支持用户自定义收紧 |
| 护栏规则过于严格导致正常命令被拦截 | 可用性差 | 用户可通过审批通过合法命令，规则可配置 |
| HITL 审批频繁打断用户 | 体验差 | 审批规则可配置粒度，支持批量审批 |
| OS keyring 在某些环境不可用 | 凭据无法存储 | 提供加密文件备选方案 |
| Docker 容器内 keyring 不可用 | 分发体验差 | 支持挂载加密文件，文档说明清楚 |
| Token 预算控制不当导致上下文溢出 | LLM 调用失败 | 滑动窗口 + 裁剪策略，配置化 token 预算 |

---

> **下一步：** 本 SPEC 经用户确认后，将触发 `writing-plans` 技能生成 `PLAN.md`。