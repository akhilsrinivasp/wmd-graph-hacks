"""Safety agent: independent checks before a pharmacist sees the order.

Checks drug allergy and cross-reactivity, drug-drug and drug-condition
problems, the dose against weight-based rules, the chosen base again
(defence in depth), and whether a suitable commercial product exists
(503A pharmacies should not compound copies of available products).
"""
from compounder import db
from compounder import queries as Q
from compounder.agents.base import Agent, props
from compounder.agents.formulation import acceptable_forms, conflicts_for


class SafetyAgent(Agent):
    name = "Safety"
    handles_status = "FORMULATED"
    next_status = "SAFETY_CHECKED"

    def run(self, order_id: str) -> None:
        ctx = self.context(order_id)
        rx, patient, drug = ctx["rx"], ctx["patient"], ctx["drug"]
        pid, did = patient["id"], drug["id"]
        counts = {"block": 0, "warn": 0, "info": 0}

        def add(sev, cat, msg, evidence=None, about=None):
            counts[sev] += 1
            self.finding(order_id, sev, cat, msg, evidence, about)

        # 1. Drug allergy and cross-reactivity
        for r in db.run(Q.DRUG_ALLERGY, {"patient_id": pid, "drug_id": did}):
            add("block", "allergy", f"Patient is allergic to {r['allergy']} and {drug['name']} is one.",
                [" → ".join(r["chain"])], [did])
        for r in db.run(Q.DRUG_CROSS_REACTIVITY, {"patient_id": pid, "drug_id": did}):
            add(r["severity"], "allergy",
                f"Allergy to {r['allergy']}: possible cross-reactivity with {r['drug_class']}. {r['note']}")

        # 2. Drug-drug interactions with current meds
        for r in db.run(Q.DRUG_INTERACTIONS, {"patient_id": pid, "drug_id": did}):
            add(r["severity"], "interaction", f"{drug['name']} + {r['other_drug']}: {r['effect']}",
                [f"{drug['name']} is a {r['via']}; {r['other_drug']} is a {r['other_via']}"])

        # 3. Drug-condition cautions
        for r in db.run(Q.DRUG_CONDITION_CAUTIONS, {"patient_id": pid, "drug_id": did}):
            add(r["severity"], "condition", f"{r['condition']}: {r['note']}", [f"{drug['name']} → {r['via']}"])

        # 4. Dose check
        self._dose_check(rx, patient, drug, add)

        # 5. Re-check the chosen base
        form = db.run(Q.ORDER_RESULT, {"order_id": order_id})[0]
        formulation = props(form["f"])
        if formulation:
            base_id = db.run("MATCH (:Order {id: $o})-[:PROPOSED]->(:Formulation)-[:USES_BASE]->(b:Base) "
                             "RETURN b.id AS id", {"o": order_id})[0]["id"]
            meds = [r["id"] for r in db.run("MATCH (:Patient {id: $p})-[:TAKES]->(d:Drug) RETURN d.id AS id", {"p": pid})]
            for issue in conflicts_for([base_id], pid, [did, *meds])[base_id]:
                add(issue["severity"], "ingredient", issue["message"], [" → ".join(issue["chain"])], [base_id])
            for note in formulation.get("notes") or []:
                add("info", "supply", note)

        # 6. Commercial alternatives (regulatory)
        self._commercial_check(rx, patient, drug, add)

        self.log(order_id, "safety_review",
                 f"{counts['block']} blocking, {counts['warn']} warning, {counts['info']} info finding(s).",
                 used_ids=[pid, did])
        self.set_status(order_id, self.next_status)

    def _dose_check(self, rx, patient, drug, add):
        population = "pediatric" if patient["age_years"] < 18 else "adult"
        rows = db.run(Q.DOSE_RULE, {"drug_id": drug["id"], "population": population})
        if not rows:
            add("warn", "dose", f"No {population} dose rule for {drug['name']} in the knowledge base; check manually.")
            return
        rule = props(rows[0]["r"])

        if rx.get("route") == "topical":
            pct, cap = rx.get("concentration_pct"), rule.get("max_concentration_pct")
            if pct is not None and cap is not None and pct > cap:
                add("warn", "dose", f"{drug['name']} {pct}% is above the usual maximum of {cap}%.")
            return

        daily = rx["dose_mg"] * int(rx.get("frequency_per_day") or 1)
        weight = patient.get("weight_kg")
        evidence = [f"{rx['dose_mg']} mg × {rx.get('frequency_per_day')}/day = {daily:g} mg/day"]
        blocks, warns = [], []
        if weight and rule.get("mg_per_kg_day_max") is not None:
            per_kg = daily / weight
            evidence.append(f"{daily:g} mg ÷ {weight:g} kg = {per_kg:.2f} mg/kg/day")
            lo, hi = rule.get("mg_per_kg_day_min"), rule["mg_per_kg_day_max"]
            if per_kg > hi:
                blocks.append(f"Dose is {per_kg:.1f} mg/kg/day, above the {population} maximum of {hi:g} mg/kg/day.")
            elif lo is not None and per_kg < lo:
                warns.append(f"Dose is {per_kg:.2f} mg/kg/day, below the usual {population} range ({lo:g}–{hi:g} mg/kg/day).")
        # Absolute limits are checked regardless of the weight-based result.
        if rule.get("mg_day_max") is not None and daily > rule["mg_day_max"]:
            blocks.append(f"{daily:g} mg/day exceeds the maximum of {rule['mg_day_max']:g} mg/day.")
        if rule.get("mg_day_min") is not None and daily < rule["mg_day_min"]:
            warns.append(f"{daily:g} mg/day is below the usual minimum of {rule['mg_day_min']:g} mg/day.")
        for msg in blocks:
            add("block", "dose", msg + " Contact the prescriber.", evidence)
        for msg in warns:
            add("warn", "dose", msg, evidence)
        if not blocks and not warns:
            add("info", "dose", f"Dose is within the {population} range.", evidence)

    def _commercial_check(self, rx, patient, drug, add):
        route = rx.get("route", "oral")
        preferred, _ = acceptable_forms(patient["id"], route)
        forms = preferred or ([f["id"] for f in db.run(
            "MATCH (f:DosageForm {route: $r}) RETURN f.id AS id", {"r": route})])
        products = db.run(Q.COMMERCIAL_PRODUCTS, {"drug_id": drug["id"], "form_ids": forms})
        if not products:
            add("info", "regulatory", f"No FDA-labeled {drug['name']} product found in an acceptable form "
                "(openFDA snapshot). Compounding is justified on availability.")
            return
        meds = [r["id"] for r in db.run("MATCH (:Patient {id: $p})-[:TAKES]->(d:Drug) RETURN d.id AS id", {"p": patient["id"]})]
        conflicts = conflicts_for([p["product_id"] for p in products], patient["id"], [drug["id"], *meds])
        suitable = [p for p in products if not any(c["severity"] == "block" for c in conflicts[p["product_id"]])]
        if suitable:
            names = "; ".join(f"{p['brand']} ({p['manufacturer']}, {p['form'].lower()})" for p in suitable[:3])
            add("warn", "regulatory",
                f"{len(suitable)} commercial product(s) look suitable for this patient: {names}. "
                "Under FDA section 503A, document the clinical reason a compounded version is needed.",
                [p["source"] for p in suitable[:3]])
        else:
            reasons = sorted({c["message"] for p in products for c in conflicts[p["product_id"]]
                              if c["severity"] == "block"})
            add("info", "regulatory",
                f"All {len(products)} commercial {drug['name']} products checked contain something this patient "
                "can't take, so compounding is justified.", reasons[:5])
