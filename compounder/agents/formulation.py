"""Formulation agent: picks dosage form, base and strength, then works out
how much to make and the label directions.

Every candidate base comes from the graph (drug -STABLE_IN-> base), and is
excluded or ranked using graph conflict queries. Excluded options are kept
with their reason so the pharmacist can see why they were not chosen.
"""
import math

from compounder import db, procedure
from compounder import queries as Q
from compounder.agents.base import Agent, new_id

STORAGE_TEXT = {"refrigerate": "Keep in the refrigerator.", "room temperature": "Store at room temperature."}


def _fmt(x: float) -> str:
    return f"{x:g}"


def conflicts_for(item_ids: list[str], patient_id: str, drug_ids: list[str]) -> dict[str, list[dict]]:
    """Run the three ingredient conflict queries for a set of bases or products.

    Returns {item_id: [{severity, kind, message, chain}]}.
    """
    out: dict[str, list[dict]] = {i: [] for i in item_ids}
    if not item_ids:
        return out
    params = {"item_ids": item_ids, "patient_id": patient_id, "drug_ids": drug_ids}
    for r in db.run(Q.INGREDIENT_ALLERGY_CONFLICTS, params):
        why = {"ALLERGIC_TO": "allergic to", "AVOIDS": "avoids", "HAD_REACTION": "previously reacted to"}[r["relation"]]
        out[r["item_id"]].append({
            "severity": "block", "kind": "allergy",
            "message": f"Contains {r['ingredient']}; patient {why} {r['trigger']}.",
            "chain": r["chain"]})
    for r in db.run(Q.INGREDIENT_CONDITION_CONFLICTS, params):
        out[r["item_id"]].append({
            "severity": r["severity"], "kind": "condition",
            "message": f"Contains {r['ingredient']}: {r['note']} (patient has {r['condition']}).",
            "chain": r["chain"]})
    for r in db.run(Q.INGREDIENT_DRUG_INTERACTIONS, params):
        out[r["item_id"]].append({
            "severity": r["severity"], "kind": "interaction",
            "message": f"Contains {r['ingredient']}, which interacts with {r['drug']}: {r['effect']}",
            "chain": [r["ingredient"], r["drug"]]})
    return out


def acceptable_forms(patient_id: str, route: str) -> tuple[list[str], list[str]]:
    """Forms the patient's conditions call for, and the reasons."""
    rows = db.run(Q.PREFERRED_FORMS, {"patient_id": patient_id})
    forms = sorted({r["form_id"] for r in rows})
    reasons = sorted({r["because"] for r in rows})
    if route != "oral":
        return [], []
    return forms, reasons


class FormulationAgent(Agent):
    name = "Formulation"
    handles_status = "CONTEXT_READY"
    next_status = "FORMULATED"

    def run(self, order_id: str) -> None:
        ctx = self.context(order_id)
        rx, patient, drug = ctx["rx"], ctx["patient"], ctx["drug"]
        route = rx.get("route", "oral")

        candidates = db.run(Q.CANDIDATE_BASES, {"drug_id": drug["id"], "route": route})
        if not candidates:
            self.finding(order_id, "block", "formulation",
                         f"No compounding formula for {drug['name']} ({route}) in the knowledge base. "
                         "Consider a commercial product.", about_ids=[drug["id"]])
            self.log(order_id, "find_bases", f"No known stable base for {drug['name']} by {route} route.",
                     used_ids=[drug["id"]])
            self.set_status(order_id, self.next_status)
            return

        preferred, reasons = acceptable_forms(patient["id"], route)
        if preferred:
            in_pref = [c for c in candidates if c["form_id"] in preferred]
            if in_pref:
                candidates = in_pref
                self.log(order_id, "choose_form",
                         f"Patient needs a liquid because of: {', '.join(reasons)}.", used_ids=preferred)
            else:
                self.finding(order_id, "warn", "formulation",
                             f"Patient needs a liquid ({', '.join(reasons)}) but no stable liquid formula is known "
                             f"for {drug['name']}.")

        patient_drugs = [r["id"] for r in db.run(
            "MATCH (:Patient {id: $p})-[:TAKES]->(d:Drug) RETURN d.id AS id", {"p": patient["id"]})]
        tolerated = {r["id"] for r in db.run(
            "MATCH (:Patient {id: $p})-[:TOLERATED]->(b:Base) RETURN b.id AS id", {"p": patient["id"]})}
        conflicts = conflicts_for([c["base_id"] for c in candidates], patient["id"], [drug["id"], *patient_drugs])

        ranked, excluded = [], []
        for c in candidates:
            issues = conflicts[c["base_id"]]
            blocks = [i for i in issues if i["severity"] == "block"]
            if blocks:
                excluded.append(f"{c['base']}: {blocks[0]['message']}")
                continue
            warns = [i for i in issues if i["severity"] == "warn"]
            score = (5 if c["base_id"] in tolerated else 0) + (2 if c["has_study"] else 0) \
                - 3 * len(warns) + c["bud_days"] / 100
            ranked.append((score, c, warns))
        ranked.sort(key=lambda t: -t[0])

        self.log(order_id, "screen_bases",
                 f"{len(candidates)} candidate base(s); {len(excluded)} excluded. " +
                 " | ".join(excluded[:6]),
                 used_ids=[c["base_id"] for c in candidates])

        if not ranked:
            self.finding(order_id, "block", "formulation",
                         "Every known base conflicts with this patient. Pharmacist must design a custom formula.",
                         evidence=excluded)
            self.set_status(order_id, self.next_status)
            return

        _score, best, _warns = ranked[0]
        plan = self._dosing(rx, best)
        mfr = procedure.build(drug["id"], drug["name"], best, plan, rx)
        props = {
            "id": new_id("form"),
            "drug": drug["name"], "base": best["base"], "form": best["form"],
            "concentration": plan["concentration"], "dose_text": plan["dose_text"],
            "quantity": plan["quantity"], "quantity_unit": plan["quantity_unit"],
            "days_supplied": plan["days"], "bud_days": best["bud_days"],
            "bud_source": best["reference"], "storage": best["storage"] or "",
            "directions": plan["directions"], "notes": plan["notes"],
            "excluded": excluded,
            "procedure": mfr["procedure"], "ingredients": mfr["ingredients"], "equipment": mfr["equipment"],
            "qc": mfr["qc"], "label_text": mfr["label"],
            "alternatives": [f"{c['base']} (score {s:.1f})" for s, c, _ in ranked[1:4]],
        }
        db.run("MATCH (o:Order {id: $id})-[:PROPOSED]->(old:Formulation) DETACH DELETE old", {"id": order_id})
        db.run(Q.WRITE_FORMULATION, {"order_id": order_id, "drug_id": drug["id"], "base_id": best["base_id"],
                                     "form_id": best["form_id"], "props": props})
        why = "previously tolerated, " if best["base_id"] in tolerated else ""
        self.log(order_id, "propose_formulation",
                 f"{drug['name']} {plan['concentration']} {best['form'].lower()} in {best['base']} "
                 f"({why}{'stability study' if best['has_study'] else 'USP <795> default BUD'}, "
                 f"BUD {best['bud_days']} days). {plan['dose_text']}. Make {plan['quantity']} {plan['quantity_unit']}.",
                 used_ids=[best["base_id"], best["form_id"], drug["id"]])
        self.set_status(order_id, self.next_status)

    @staticmethod
    def _dosing(rx: dict, base: dict) -> dict:
        freq = int(rx.get("frequency_per_day") or 1)
        duration = int(rx.get("duration_days") or 30)
        days = min(duration, int(base["bud_days"]))
        notes = []
        if duration > days:
            notes.append(f"Beyond-use date is {base['bud_days']} days: dispense {days} days now, "
                         f"remaining {duration - days} days as refills.")
        storage = STORAGE_TEXT.get(base.get("storage") or "", "")
        times = {1: "once daily", 2: "twice daily", 3: "three times daily", 4: "four times daily"}.get(freq, f"{freq} times daily")

        if base["liquid"]:
            conc = base["conc_mg_per_ml"]
            dose_ml = round(rx["dose_mg"] / conc, 2)
            total = math.ceil(dose_ml * freq * days / 5) * 5 + 5  # round up + 5 mL overage
            return {
                "concentration": f"{_fmt(conc)} mg/mL", "quantity": total, "quantity_unit": "mL", "days": days,
                "dose_text": f"{_fmt(rx['dose_mg'])} mg = {_fmt(dose_ml)} mL {times}",
                "directions": f"Give {_fmt(dose_ml)} mL by mouth {times}. Shake well before use. {storage}".strip(),
                "notes": notes,
            }
        if base["form_id"] == "capsule":
            mg = rx["dose_mg"]
            strength = f"{_fmt(mg * 1000)} mcg" if mg < 1 else f"{_fmt(mg)} mg"
            return {
                "concentration": f"{strength}/capsule", "quantity": freq * days, "quantity_unit": "capsules",
                "days": days, "dose_text": f"1 capsule ({strength}) {times}",
                "directions": f"Take 1 capsule by mouth {times}. {storage}".strip(), "notes": notes,
            }
        # topical
        pct = rx.get("concentration_pct")
        grams = int(rx.get("quantity") or 30)
        return {
            "concentration": f"{_fmt(pct)}%", "quantity": grams, "quantity_unit": "g", "days": days,
            "dose_text": f"Apply {times}",
            "directions": f"Apply a thin layer to the affected area {times}. {rx.get('notes') or ''} {storage}".strip(),
            "notes": notes,
        }
