"""Load the knowledge base, openFDA products and demo patients into FalkorDB.

Usage:  python -m compounder.seed.loader            (reset + load everything)
"""
from compounder import db
from compounder.seed import demo_patients as demo
from compounder.seed import insurance as ins
from compounder.seed import knowledge as kb
from compounder.seed.openfda import load_snapshot

LABELS = ["Drug", "DrugClass", "Excipient", "ExcipientGroup", "Condition", "DosageForm", "Base",
          "DoseRule", "Product", "Patient", "Prescriber", "Prescription", "Order", "Formulation",
          "Finding", "AgentStep", "Review", "InsurancePlan", "FormularyEntry", "CoverageDecision", "PolicyChunk"]


def reset():
    try:
        db.graph().delete()
    except Exception:
        pass  # graph did not exist yet
    for label in LABELS:
        db.run(f"CREATE INDEX FOR (n:{label}) ON (n.id)")


def _link_by_id(rows: list[dict], rel: str):
    """rows: [{src, dst, props}] linking any two nodes by their id property."""
    db.run(
        f"""UNWIND $rows AS r
        MATCH (a {{id: r.src}}) MATCH (b {{id: r.dst}})
        MERGE (a)-[e:{rel}]->(b) SET e += r.props""",
        {"rows": rows},
    )


def load_knowledge():
    db.run("UNWIND $rows AS r CREATE (:DrugClass {id: r[0], name: r[1]})",
           {"rows": [[c[0], c[1]] for c in kb.DRUG_CLASSES]})
    db.run("UNWIND $rows AS r CREATE (:Drug {id: r[0], name: r[1], aliases: r[2]})",
           {"rows": [[d[0], d[1], d[3]] for d in kb.DRUGS]})
    isa = [{"src": c[0], "dst": c[2], "props": {}} for c in kb.DRUG_CLASSES if c[2]]
    isa += [{"src": d[0], "dst": d[2], "props": {}} for d in kb.DRUGS]
    isa += [{"src": a, "dst": b, "props": {}} for a, b in kb.EXTRA_CLASS_LINKS]

    db.run("UNWIND $rows AS r CREATE (:ExcipientGroup {id: r[0], name: r[1]})",
           {"rows": [[g[0], g[1]] for g in kb.EXCIPIENT_GROUPS]})
    db.run("UNWIND $rows AS r CREATE (:Excipient {id: r[0], name: r[1], aliases: r[2]})",
           {"rows": [[e[0], e[1], e[3]] for e in kb.EXCIPIENTS]})
    isa += [{"src": g[0], "dst": g[2], "props": {}} for g in kb.EXCIPIENT_GROUPS if g[2]]
    isa += [{"src": e[0], "dst": p, "props": {}} for e in kb.EXCIPIENTS for p in e[2]]
    _link_by_id(isa, "IS_A")

    db.run("UNWIND $rows AS r CREATE (:Condition {id: r[0], name: r[1]})",
           {"rows": [list(c) for c in kb.CONDITIONS]})
    db.run("UNWIND $rows AS r CREATE (:DosageForm {id: r[0], name: r[1], route: r[2], liquid: r[3]})",
           {"rows": [list(f) for f in kb.DOSAGE_FORMS]})

    _link_by_id([{"src": a, "dst": b, "props": {"severity": s, "effect": e}}
                 for a, b, s, e in kb.INTERACTIONS], "INTERACTS_WITH")
    _link_by_id([{"src": a, "dst": b, "props": {"severity": s, "note": n}}
                 for a, b, s, n in kb.CROSS_REACTIVITY], "CROSS_REACTS_WITH")
    _link_by_id([{"src": a, "dst": c, "props": {"severity": s, "note": n}}
                 for a, c, s, n in kb.DRUG_CAUTIONS + kb.EXCIPIENT_AVOID_IN], "CAUTION_IN")
    _link_by_id([{"src": c, "dst": f, "props": {}} for c, f in kb.CONDITION_PREFERS_FORM], "PREFERS_FORM")

    for b in kb.BASES:
        default_bud = kb.USP_795_DEFAULT_BUD[(b["aqueous"], b["preserved"])]
        db.run(
            """CREATE (base:Base {id: $id, name: $name, aqueous: $aq, preserved: $pr, usp_default_bud_days: $bud})
            WITH base MATCH (f:DosageForm {id: $form}) CREATE (base)-[:FOR_FORM]->(f)
            WITH base UNWIND $contains AS ex MATCH (e:Excipient {id: ex}) CREATE (base)-[:CONTAINS]->(e)""",
            {"id": b["id"], "name": b["name"], "aq": b["aqueous"], "pr": b["preserved"],
             "bud": default_bud, "form": b["form"], "contains": b["contains"]},
        )

    _link_by_id([{"src": d, "dst": b, "props": {
        "conc_mg_per_ml": conc, "bud_days": bud, "storage": storage,
        "reference": ref or "No product-specific study: USP <795> default beyond-use date applies"}}
        for d, b, conc, bud, storage, ref in kb.STABILITY], "STABLE_IN")

    rules = []
    for drug, pop, kmin, kmax, dmin, dmax, pct in kb.DOSE_RULES:
        rules.append({"id": f"dose_{drug}_{pop}", "drug": drug, "props": {
            "population": pop, "mg_per_kg_day_min": kmin, "mg_per_kg_day_max": kmax,
            "mg_day_min": dmin, "mg_day_max": dmax, "max_concentration_pct": pct}})
    db.run("""UNWIND $rows AS r MATCH (d:Drug {id: r.drug})
              CREATE (d)-[:HAS_DOSE_RULE]->(x:DoseRule {id: r.id}) SET x += r.props""", {"rows": rules})


def load_products():
    snapshot = load_snapshot()
    rows = []
    for drug_id, products in snapshot.items():
        for p in products:
            rows.append({"id": f"prod_{p['id']}_{drug_id}", "drug": drug_id, "form": p["form"],
                         "brand": p["brand"], "manufacturer": p["manufacturer"],
                         "source": p["source"], "excipients": p["excipients"]})
    db.run(
        """UNWIND $rows AS r
        MATCH (d:Drug {id: r.drug}) MATCH (f:DosageForm {id: r.form})
        CREATE (p:Product {id: r.id, brand: r.brand, manufacturer: r.manufacturer, source: r.source})
        CREATE (p)-[:OF_DRUG]->(d) CREATE (p)-[:IN_FORM]->(f)
        WITH p, r UNWIND r.excipients AS ex
        MATCH (e:Excipient {id: ex}) CREATE (p)-[:CONTAINS]->(e)""",
        {"rows": rows},
    )
    return len(rows)


def load_insurance():
    db.run("UNWIND $rows AS r CREATE (p:InsurancePlan) SET p = r", {"rows": ins.PLANS})
    rows = [{"id": f"fe_{plan}_{drug}_{form}", "plan": plan, "drug": drug, "form": form,
             "props": {"status": status, "tier": tier, "copay_usd": copay, "prior_auth": pa, "note": note}}
            for plan, drug, form, status, tier, copay, pa, note in ins.FORMULARY]
    db.run(
        """UNWIND $rows AS r
        MATCH (pl:InsurancePlan {id: r.plan}) MATCH (d:Drug {id: r.drug}) MATCH (f:DosageForm {id: r.form})
        CREATE (fe:FormularyEntry {id: r.id}) SET fe += r.props
        CREATE (pl)-[:LISTS]->(fe) CREATE (fe)-[:FOR_DRUG]->(d) CREATE (fe)-[:IN_FORM]->(f)""",
        {"rows": rows},
    )
    _link_by_id([{"src": a, "dst": b, "props": {"note": n}} for a, b, n in ins.THERAPEUTIC_ALTERNATIVES],
                "ALTERNATIVE_TO")


def load_demo_people():
    db.run("UNWIND $rows AS r CREATE (p:Prescriber) SET p = r", {"rows": demo.PRESCRIBERS})
    for p in demo.PATIENTS:
        plan = ins.PATIENT_PLANS.get(p["id"])
        if plan and "insurance" not in p:
            p = {**p, "insurance": {"plan_id": plan[0], "member_id": plan[1]}}
        add_patient(p)
    for rx in demo.PRESCRIPTIONS:
        add_prescription(rx)
        create_order(rx["id"], source="e-prescription")


def add_patient(p: dict):
    db.run("""CREATE (:Patient {id: $id, name: $name, age_years: $age, weight_kg: $wt, sex: $sex, story: $story})""",
           {"id": p["id"], "name": p["name"], "age": float(p["age_years"]), "wt": float(p["weight_kg"]),
            "sex": p.get("sex", ""), "story": p.get("story", "")})
    # Conditions and allergies may be plain ids or dicts with details
    # (e.g. {"id": "azo_dye", "reaction": "hives", "severity": "moderate"}).
    def rows(items, defaults):
        out = []
        for it in items:
            it = {"id": it} if isinstance(it, str) else dict(it)
            props = {**defaults, **{k: v for k, v in it.items() if k != "id" and v not in (None, "")}}
            out.append({"src": p["id"], "dst": it["id"], "props": props})
        return out
    _link_by_id(rows(p.get("conditions", []), {"derived": False}), "HAS_CONDITION")
    _link_by_id(rows(p.get("allergies", []), {}), "ALLERGIC_TO")
    _link_by_id([{"src": p["id"], "dst": a, "props": {}} for a in p.get("avoids", [])], "AVOIDS")
    _link_by_id(rows(p.get("takes", []), {}), "TAKES")
    plan = p.get("insurance") or {}
    if plan.get("plan_id"):
        _link_by_id([{"src": p["id"], "dst": plan["plan_id"], "props": {"member_id": plan.get("member_id", "")}}],
                    "INSURED_BY")


def add_prescription(rx: dict):
    props = {k: rx.get(k) for k in ("id", "route", "dose_mg", "concentration_pct", "frequency_per_day",
                                    "duration_days", "quantity", "notes")}
    db.run(
        """MATCH (pt:Patient {id: $patient}) MATCH (doc:Prescriber {id: $prescriber}) MATCH (d:Drug {id: $drug})
        CREATE (rx:Prescription) SET rx = $props
        CREATE (doc)-[:WROTE]->(rx) CREATE (rx)-[:FOR_PATIENT]->(pt) CREATE (rx)-[:PRESCRIBES]->(d)""",
        {"patient": rx["patient"], "prescriber": rx["prescriber"], "drug": rx["drug"],
         "props": {k: v for k, v in props.items() if v is not None}},
    )


def create_order(rx_id: str, source: str = "e-prescription", raw_text: str | None = None) -> str:
    import time
    import uuid
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    db.run(
        """MATCH (rx:Prescription {id: $rx})
        CREATE (o:Order {id: $id, status: 'RECEIVED', source: $source, raw_text: $raw, created_at: $ts})
        CREATE (o)-[:FILLS]->(rx)""",
        {"rx": rx_id, "id": order_id, "source": source, "raw": raw_text or "", "ts": int(time.time())},
    )
    return order_id


def load_all():
    reset()
    load_knowledge()
    n = load_products()
    load_insurance()
    load_demo_people()
    from compounder import policy
    policy.load()
    return n


if __name__ == "__main__":
    n = load_all()
    counts = db.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY n DESC")
    print(f"Loaded {n} commercial products.")
    for c in counts:
        print(f"  {c['label']:<15} {c['n']}")
