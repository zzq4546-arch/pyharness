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