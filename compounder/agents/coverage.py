"""Coverage agent: finds the safe option the patient's insurance pays for
with the least friction (no prior auth, lowest copay), then drafts the
message to the prescriber and, if needed, the prior-authorization request.

Doctors usually write just the drug. Plans often cover one dosage form and
deny another, or prefer one brand. The pharmacist knows this; the graph lets
the agent know it too: plan -> formulary entry -> drug + form, joined with the
commercial products in that form and the patient's ingredient conflicts.
"""
from compounder import db
from compounder import queries as Q
from compounder.agents.base import Agent, new_id, props
from compounder.agents.formulation import acceptable_forms, conflicts_for


def _money(x) -> str:
    return f"${x:g}" if x is not None else "?"


class CoverageAgent(Agent):
    name = "Coverage"
    handles_status = "SAFETY_CHECKED"
    next_status = "AWAITING_REVIEW"

    def run(self, order_id: str) -> None:
        ctx = self.context(order_id)
        rx, patient, drug, doc = ctx["rx"], ctx["patient"], ctx["drug"], ctx["prescriber"]
        plan_rows = db.run(Q.PATIENT_PLAN, {"patient_id": patient["id"]})
        if not plan_rows:
            self.finding(order_id, "info", "coverage", "No insurance on file: patient pays cash.")
            self.set_status(order_id, self.next_status)
            return
        plan, member_id = props(plan_rows[0]["pl"]), plan_rows[0]["member_id"]

        route = rx.get("route", "oral")
        forms, _ = acceptable_forms(patient["id"], route)
        if not forms:
            forms = [r["id"] for r in db.run("MATCH (f:DosageForm {route: $r}) RETURN f.id AS id", {"r": route})]
        alts = db.run(Q.THERAPEUTIC_ALTERNATIVES, {"drug_id": drug["id"]})
        drug_ids = [drug["id"], *[a["id"] for a in alts]]
        meds = [r["id"] for r in db.run("MATCH (:Patient {id: $p})-[:TAKES]->(d:Drug) RETURN d.id AS id",
                                        {"p": patient["id"]})]

        entries = db.run(Q.COVERAGE_ENTRIES, {"patient_id": patient["id"], "drug_ids": drug_ids, "form_ids": forms})
        products = []
        for did in drug_ids:
            for p in db.run(Q.COMMERCIAL_PRODUCTS, {"drug_id": did, "form_ids": forms}):
                products.append({**p, "drug_id": did})
        conflicts = conflicts_for([p["product_id"] for p in products], patient["id"], [*drug_ids, *meds])

        options, denied = [], []
        for e in entries:
            prods = [p for p in products if p["drug_id"] == e["drug_id"] and p["form"] == e["form"]]
            safe = [p for p in prods if not any(c["severity"] == "block" for c in conflicts[p["product_id"]])]
            label = f"{e['drug']} {e['form'].lower()}"
            if e["status"] == "excluded":
                denied.append(f"{label}: not covered. {e['note']}".strip())
            elif not prods:
                denied.append(f"{label}: covered, but no commercial product in the snapshot.")
            elif not safe:
                why = next(c["message"] for p in prods for c in conflicts[p["product_id"]] if c["severity"] == "block")
                denied.append(f"{label}: covered, but every product conflicts with the patient ({why})")
            else:
                options.append({"kind": "commercial", "label": label, "drug_id": e["drug_id"], "drug": e["drug"],
                                "form": e["form"], "copay": e["copay"], "pa": bool(e["prior_auth"]),
                                "tier": e["tier"], "note": e["note"] or "",
                                "products": [f"{p['brand']} ({p['manufacturer']})" for p in safe[:2]]})

        formulation = props((db.run(Q.ORDER_RESULT, {"order_id": order_id}) or [{}])[0].get("f"))
        if formulation and plan.get("compound_covered"):
            pa = bool(plan.get("compound_pa")) or (plan["type"] == "medicaid" and patient["age_years"] >= 21)
            options.append({"kind": "compound", "label": f"compounded {formulation['drug']} {formulation['concentration']} "
                            f"{formulation['form'].lower()}", "drug_id": drug["id"], "drug": drug["name"],
                            "form": formulation["form"], "copay": plan.get("compound_copay"), "pa": pa,
                            "tier": None, "note": plan.get("compound_rule", ""), "products": []})

        # Least friction: no prior auth, then lowest copay, then no change of drug.
        options.sort(key=lambda o: (o["pa"], o["copay"] if o["copay"] is not None else 1e9,
                                    o["drug_id"] != drug["id"]))
        option_lines = [f"{o['label']}: {_money(o['copay'])} copay{', prior auth' if o['pa'] else ''}"
                        + (f" ({', '.join(o['products'])})" if o["products"] else "") for o in options]

        if not options:
            decision = {"route": "none", "recommended": "Nothing covered for this patient",
                        "copay_usd": None, "prior_auth": False,
                        "prescriber_message": "", "pa_request": ""}
            self.finding(order_id, "warn", "coverage",
                         f"{plan['name']} covers no option that is safe for this patient. Discuss cash price or an appeal.",
                         denied[:5])
        else:
            best = options[0]
            decision = self._decide(best, rx, patient, drug, doc, plan, member_id, denied, formulation)
            msg = f"Best covered option on {plan['name']}: {best['label']} at {_money(best['copay'])} copay" + \
                  (" (prior auth needed)." if best["pa"] else ", no prior auth.")
            self.finding(order_id, "warn" if best["kind"] != "compound" else "info", "coverage", msg, denied[:5])

        blockers = db.run("MATCH (:Order {id: $o})-[:HAS_FINDING]->(f:Finding {severity: 'block'}) RETURN count(f) AS n",
                          {"o": order_id})[0]["n"]
        if blockers and decision.get("prescriber_message"):
            decision["prescriber_message"] = (f"SAFETY HOLD: {blockers} blocking safety finding(s) must be resolved "
                                              "with the prescriber before this is filled.\n\n"
                                              + decision["prescriber_message"])
        props_out = {"id": new_id("cov"), "plan": plan["name"], "member_id": member_id or "",
                     "options": option_lines, "denied": denied, **decision}
        db.run(Q.WRITE_COVERAGE, {"order_id": order_id, "plan_id": plan["id"], "props": props_out})
        self.log(order_id, "check_coverage",
                 f"{plan['name']}: {len(options)} covered option(s), {len(denied)} denied or unsuitable. "
                 f"Recommend: {decision['recommended']}.", used_ids=[plan["id"], drug["id"]])
        self.set_status(order_id, self.next_status)

    @staticmethod
    def _decide(best, rx, patient, drug, doc, plan, member_id, denied, formulation) -> dict:
        dose = (f"{rx['dose_mg']:g} mg" if rx.get("dose_mg") is not None else f"{rx.get('concentration_pct'):g}%")
        freq = rx.get("frequency_per_day")
        who = f"{patient['name']} (member ID {member_id}, {plan['name']})"
        doctor = doc.get("name", "Doctor")
        denied_txt = "".join(f"\n  - {d}" for d in denied)
        if best["kind"] == "compound":
            pa_request = ""
            if best["pa"]:
                pa_request = (
                    f"Prior authorization request: compounded {formulation['drug']} {formulation['concentration']} "
                    f"{formulation['form'].lower()} for {who}.\n"
                    f"Prescribed by {doctor}: {drug['name']} {dose}, {freq}x/day.\n"
                    f"Medical necessity: no covered commercial product is suitable for this patient:{denied_txt or ' none found.'}\n"
                    f"Plan rule: {plan.get('compound_rule', '')}")
            return {"route": "compound", "recommended": best["label"], "copay_usd": best["copay"],
                    "prior_auth": best["pa"], "pa_request": pa_request,
                    "prescriber_message": f"{doctor}: no change needed for {patient['name']}. We will prepare "
                                          f"{best['label']}" + (" and request prior authorization." if best["pa"] else ".")}
        change = "drug" if best["drug_id"] != drug["id"] else "form"
        lines = [f"{doctor}, about {who}:",
                 f"You prescribed {drug['name']} {dose}, {freq}x/day."]
        if change == "drug":
            lines.append(f"{plan['name']} does not cover a suitable form of {drug['name']}, but it covers "
                         f"{best['label']} at {_money(best['copay'])} copay"
                         f"{' (prior auth)' if best['pa'] else ', no prior auth'}. {best['note']}")
            lines.append(f"Would you consider switching? If yes, please send a new prescription for {best['label']}.")
        else:
            lines.append(f"{plan['name']} covers {best['label']} ({', '.join(best['products'])}) at "
                         f"{_money(best['copay'])} copay{' with prior auth' if best['pa'] else ', no prior auth'}. "
                         f"{best['note']}")
            lines.append(f"Please send a new prescription specifying {drug['name']} {best['form'].lower()}, {dose} "
                         f"{freq}x/day, so the claim is not denied.")
        if denied:
            lines.append("Not covered or unsuitable:" + denied_txt)
        lines.append("I checked these products against the patient's allergies and conditions.")
        return {"route": "alternative" if change == "drug" else "commercial", "recommended": best["label"],
                "copay_usd": best["copay"], "prior_auth": best["pa"], "pa_request": "",
                "prescriber_message": "\n".join(lines)}
