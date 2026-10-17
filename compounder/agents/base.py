"""Shared agent plumbing.

Agents never call each other. They coordinate through the graph: each agent
picks up an Order in the status it owns, does its work, records what it did
as AgentStep nodes linked to the evidence it used, then moves the Order on.
"""
import time
import uuid

from compounder import db
from compounder import queries as Q


def props(node) -> dict:
    """FalkorDB Node -> plain dict (None stays None)."""
    if node is None:
        return {}
    return dict(node.properties)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class Agent:
    name = "agent"
    handles_status: str = ""
    next_status: str = ""

    def run(self, order_id: str) -> None:
        raise NotImplementedError

    # --- helpers shared by all agents ---
    def log(self, order_id: str, action: str, summary: str, used_ids: list[str] | None = None):
        db.run(Q.LOG_STEP, {"order_id": order_id, "id": new_id("step"), "agent": self.name,
                            "action": action, "summary": summary, "at": time.time(),
                            "used_ids": used_ids or []})

    def finding(self, order_id: str, severity: str, category: str, message: str,
                evidence: list[str] | None = None, about_ids: list[str] | None = None):
        db.run(Q.WRITE_FINDING, {"order_id": order_id, "id": new_id("fd"), "severity": severity,
                                 "category": category, "message": message,
                                 "evidence": evidence or [], "about_ids": about_ids or [],
                                 "agent": self.name})

    def set_status(self, order_id: str, status: str):
        db.run(Q.SET_STATUS, {"order_id": order_id, "status": status})

    def context(self, order_id: str) -> dict:
        rows = db.run(Q.ORDER_CONTEXT, {"order_id": order_id})
        if not rows:
            return {}
        r = rows[0]
        return {"order": props(r["o"]), "rx": props(r["rx"]), "patient": props(r["p"]),
                "drug": props(r["d"]), "prescriber": props(r["doc"])}
