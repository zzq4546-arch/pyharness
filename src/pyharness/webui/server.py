from __future__ import annotations

import json
import asyncio
import threading
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
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


class ChatRequest(BaseModel):
    task: str


class ApproveRequest(BaseModel):
    approval_id: str
    decision: str  # "approve" or "reject"


class AppState:
    def __init__(self):
        self.loop: Optional[AgentLoop] = None
        self.hitl: Optional[HITLEngine] = None
        self.config: Optional[ConfigLoader] = None
        self.credential: Optional[CredentialManager] = None
        self.websocket: Optional[WebSocket] = None
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


def create_app(config: Optional[ConfigLoader] = None) -> FastAPI:
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
            return JSONResponse(status_code=404, content={"error": "No HITL engine"})
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

    def on_event(event):
        if state.websocket:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            try:
                asyncio.run_coroutine_threadsafe(
                    state.websocket.send_text(json.dumps(event, default=str)),
                    loop
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