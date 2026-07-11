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