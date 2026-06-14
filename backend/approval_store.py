"""ApprovalStore — human-in-the-loop workflow approval checkpoints.

Stores pending approvals and exposes approve/reject operations.
Integrated with workflow traces for visibility.
"""
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field


@dataclass
class ApprovalRequest:
    workflow_id: str = ""
    pending_agent: str = ""
    context_summary: str = ""
    created_at: float = 0.0
    status: str = "WAITING"  # WAITING | APPROVED | REJECTED

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "pending_agent": self.pending_agent,
            "context_summary": self.context_summary,
            "status": self.status,
            "created_at": self.created_at,
        }


class ApprovalStore:
    """In-memory store for workflow approval requests."""

    def __init__(self):
        self._pending: dict[str, ApprovalRequest] = {}
        self._history: list[ApprovalRequest] = []
        self._lock = threading.Lock()

    def request(self, workflow_id: str, agent_name: str,
                context_summary: str = "") -> ApprovalRequest:
        """Create a new approval request — workflow pauses here."""
        req = ApprovalRequest(
            workflow_id=workflow_id,
            pending_agent=agent_name,
            context_summary=context_summary,
            created_at=time.time(),
            status="WAITING",
        )
        with self._lock:
            self._pending[workflow_id] = req
        print(f"[Approval] requested for {agent_name} (wf={workflow_id})")
        return req

    def approve(self, workflow_id: str) -> dict:
        with self._lock:
            req = self._pending.pop(workflow_id, None)
            if req:
                req.status = "APPROVED"
                self._history.append(req)
                return {"ok": True, "status": "APPROVED", "agent": req.pending_agent}
        return {"ok": False, "error": "Approval not found"}

    def reject(self, workflow_id: str) -> dict:
        with self._lock:
            req = self._pending.pop(workflow_id, None)
            if req:
                req.status = "REJECTED"
                self._history.append(req)
                return {"ok": True, "status": "REJECTED", "agent": req.pending_agent}
        return {"ok": False, "error": "Approval not found"}

    def get_pending(self) -> list[dict]:
        with self._lock:
            return [r.to_dict() for r in self._pending.values()]

    def get_status(self, workflow_id: str) -> str:
        with self._lock:
            if workflow_id in self._pending:
                return self._pending[workflow_id].status
        for req in reversed(self._history):
            if req.workflow_id == workflow_id:
                return req.status
        return "NONE"


# ── Singleton ─────────────────────────────────────────────

approval_store = ApprovalStore()
