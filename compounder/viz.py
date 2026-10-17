"""Build a Graphviz picture of the evidence behind one order."""
from compounder import db
from compounder.agents.formulation import conflicts_for

COLORS = {
    "Patient": "#4C78A8", "Drug": "#F58518", "DrugClass": "#FFBF79", "Base": "#54A24B",
    "Excluded": "#E45756", "Excipient": "#B279A2", "ExcipientGroup": "#D6A5C9",
    "Condition": "#72B7B2", "DosageForm": "#9D9D9D",
}


def _q(s: str) -> str:
    return '"' + str(s).replace('"', "'") + '"'


def order_dot(order_id: str) -> str:
    ctx = db.run("""
        MATCH (o:Order {id: $id})-[:FILLS]->(rx)-[:FOR_PATIENT]->(p:Patient)
        MATCH (rx)-[:PRESCRIBES]->(d:Drug)
        OPTIONAL MATCH (o)-[:PROPOSED]->(f:Formulation)-[:USES_BASE]->(b:Base)
        OPTIONAL MATCH (f)-[:IN_FORM]->(df:DosageForm)
        RETURN p.id AS pid, p.name AS patient, d.id AS did, d.name AS drug, b.id AS bid, b.name AS base,
               df.name AS form, rx.route AS route""", {"id": order_id})
    if not ctx:
        return "digraph G {}"
    c = ctx[0]
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str, str]] = set()

    def node(name, kind):
        nodes.setdefault(name, kind)

    node(c["patient"], "Patient")
    node(c["drug"], "Drug")
    edges.add((c["patient"], c["drug"], "prescribed"))

    for r in db.run("""MATCH (p:Patient {id: $pid})-[r]->(x)
                       WHERE type(r) IN ['HAS_CONDITION','ALLERGIC_TO','AVOIDS','TAKES','TOLERATED','HAD_REACTION']
                       RETURN type(r) AS rel, x.name AS name, labels(x)[0] AS label""", {"pid": c["pid"]}):
        node(r["name"], r["label"])
        edges.add((c["patient"], r["name"], r["rel"].lower().replace("_", " ")))

    for r in db.run("MATCH path = (d:Drug {id: $did})-[:IS_A*1..3]->(:DrugClass) RETURN [n IN nodes(path) | n.name] AS chain",
                    {"did": c["did"]}):
        for a, b in zip(r["chain"], r["chain"][1:]):
            node(b, "DrugClass")
            edges.add((a, b, "is a"))

    if c["base"]:
        node(c["base"], "Base")
        edges.add((c["drug"], c["base"], "chosen base"))
        if c["form"]:
            node(c["form"], "DosageForm")
            edges.add((c["base"], c["form"], "form"))

    # Excluded bases and the ingredient path that ruled each one out
    cands = db.run("""MATCH (d:Drug {id: $did})-[:STABLE_IN]->(b:Base)-[:FOR_FORM]->(:DosageForm {route: $route})
                      RETURN b.id AS id, b.name AS name""", {"did": c["did"], "route": c["route"] or "oral"})
    meds = [r["id"] for r in db.run("MATCH (:Patient {id: $p})-[:TAKES]->(d:Drug) RETURN d.id AS id", {"p": c["pid"]})]
    conf = conflicts_for([b["id"] for b in cands], c["pid"], [c["did"], *meds])
    for b in cands:
        issues = conf[b["id"]]
        if not issues:
            continue
        blocked = any(i["severity"] == "block" for i in issues)
        if b["id"] != c["bid"]:
            node(b["name"], "Excluded" if blocked else "Base")
            edges.add((c["drug"], b["name"], "candidate"))
        for i in issues[:3]:
            chain = i["chain"]
            if not chain:
                continue
            edges.add((b["name"], chain[0], "contains"))
            node(chain[0], "Excipient")
            for x, y in zip(chain, chain[1:]):
                node(y, nodes.get(y, "ExcipientGroup"))
                edges.add((x, y, "is a" if y != chain[-1] or i["kind"] != "condition" else "caution in"))

    lines = ["digraph G {", "rankdir=LR; bgcolor=transparent; nodesep=0.25; ranksep=0.6;",
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fontcolor=white];',
             'edge [fontname="Helvetica", fontsize=9, color="#888888", fontcolor="#888888"];']
    for name, kind in nodes.items():
        lines.append(f"{_q(name)} [fillcolor={_q(COLORS.get(kind, '#888888'))}];")
    for a, b, label in edges:
        lines.append(f"{_q(a)} -> {_q(b)} [label={_q(label)}];")
    lines.append("}")
    return "\n".join(lines)
