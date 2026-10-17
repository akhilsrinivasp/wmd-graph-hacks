"""Read an order's results back out of the graph (used by the CLI and UI)."""
from compounder import db
from compounder import queries as Q
from compounder.agents.base import props


def order_report(order_id: str) -> dict:
    res = db.run(Q.ORDER_RESULT, {"order_id": order_id})
    if not res:
        return {}
    r = res[0]
    ctx = db.run(Q.ORDER_CONTEXT, {"order_id": order_id})
    c = ctx[0] if ctx else {}
    sev_rank = {"block": 0, "warn": 1, "info": 2}
    findings = sorted(db.run(Q.ORDER_FINDINGS, {"order_id": order_id}), key=lambda f: sev_rank.get(f["severity"], 3))
    return {
        "order": props(r["o"]),
        "patient": props(c.get("p")),
        "drug": props(c.get("d")),
        "rx": props(c.get("rx")),
        "prescriber": props(c.get("doc")),
        "formulation": props(r["f"]),
        "findings": findings,
        "steps": db.run(Q.ORDER_STEPS, {"order_id": order_id}),
    }
