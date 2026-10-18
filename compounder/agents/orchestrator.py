"""Runs orders through the agents.

The order's status in the graph decides which agent acts next, so the
pipeline can be resumed at any point and agents could run as separate
workers polling the graph.
"""
from compounder import db
from compounder import queries as Q
from compounder.agents.coverage import CoverageAgent
from compounder.agents.formulation import FormulationAgent
from compounder.agents.history import HistoryAgent
from compounder.agents.intake import IntakeAgent
from compounder.agents.safety import SafetyAgent

AGENTS = [IntakeAgent(), HistoryAgent(), FormulationAgent(), SafetyAgent(), CoverageAgent()]
BY_STATUS = {a.handles_status: a for a in AGENTS}


def status_of(order_id: str) -> str | None:
    rows = db.run("MATCH (o:Order {id: $id}) RETURN o.status AS s", {"id": order_id})
    return rows[0]["s"] if rows else None


def process(order_id: str, restart: bool = False) -> str:
    """Run an order until no agent handles its status. Returns the final status."""
    if restart:
        db.run(Q.CLEAR_ORDER_RESULTS, {"order_id": order_id})
        db.run(Q.SET_STATUS, {"order_id": order_id, "status": "RECEIVED"})
    for _ in range(len(AGENTS) + 1):
        status = status_of(order_id)
        agent = BY_STATUS.get(status)
        if agent is None:
            return status
        agent.run(order_id)
    return status_of(order_id)


def process_pending() -> dict[str, str]:
    pending = db.run("MATCH (o:Order) WHERE o.status IN $s RETURN o.id AS id", {"s": list(BY_STATUS)})
    return {r["id"]: process(r["id"]) for r in pending}
