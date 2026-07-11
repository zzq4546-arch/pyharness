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
        self._state = AgentState(status="IDLE")

    def run(self, task: str, on_event: callable) -> dict:
        self._stop_flag.clear()
        self._history = []
        self._feedbacks = []
        self._state = AgentState(status="IDLE")
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