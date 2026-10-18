"""Intake agent: turns an incoming order into a Prescription in the graph.

E-prescriptions arrive already structured, so the agent only validates them.
Free-text orders are parsed by the LLM (Claude or Gemini, if a key is set), then the
patient, prescriber and drug names are resolved against the graph.
"""
from compounder import db, llm
from compounder import queries as Q
from compounder.agents.base import Agent, new_id, props
from compounder.seed.loader import add_prescription


class IntakeAgent(Agent):
    name = "Intake"
    handles_status = "RECEIVED"
    next_status = "INTAKE_DONE"

    def run(self, order_id: str) -> None:
        ctx = self.context(order_id)
        if not ctx:
            ctx = self._from_free_text(order_id)
            if not ctx:
                self.set_status(order_id, "NEEDS_ATTENTION")
                return

        rx, drug = ctx["rx"], ctx["drug"]
        missing = [f for f in ("route", "frequency_per_day", "duration_days") if rx.get(f) is None]
        if rx.get("route") == "oral" and rx.get("dose_mg") is None:
            missing.append("dose_mg")
        if rx.get("route") == "topical" and rx.get("concentration_pct") is None:
            missing.append("concentration_pct")
        if missing:
            self.finding(order_id, "block", "intake", f"Prescription is missing: {', '.join(missing)}.",
                         about_ids=[rx["id"]])
            self.set_status(order_id, "NEEDS_ATTENTION")
            return

        dose = (f"{rx['dose_mg']} mg" if rx.get("dose_mg") is not None
                else f"{rx.get('concentration_pct')}%")
        self.log(order_id, "validate_prescription",
                 f"{drug['name']} {dose}, {rx.get('frequency_per_day')}x/day for {rx.get('duration_days')} days "
                 f"({rx.get('route')}) for {ctx['patient']['name']}.",
                 used_ids=[rx["id"], drug["id"], ctx["patient"]["id"]])
        self.set_status(order_id, self.next_status)

    def _from_free_text(self, order_id: str) -> dict:
        order = props(db.run("MATCH (o:Order {id: $id}) RETURN o", {"id": order_id})[0]["o"])
        text = order.get("raw_text") or ""
        if not text:
            self.finding(order_id, "block", "intake", "Order has no prescription attached.")
            return {}
        if not llm.available():
            self.finding(order_id, "block", "intake",
                         "Free-text order needs ANTHROPIC_API_KEY or GEMINI_API_KEY to be parsed. Enter it as a structured prescription instead.")
            return {}

        parsed = llm.parse_order(text)
        self.log(order_id, "parse_free_text", f"{llm.provider_label()} extracted: {parsed.model_dump_json()}")

        patient = db.run(Q.FIND_PATIENT, {"name": parsed.patient_name or ""})
        drug = db.run(Q.FIND_DRUG, {"name": parsed.drug_name or ""})
        prescriber = db.run(Q.FIND_PRESCRIBER, {"name": (parsed.prescriber_name or "").replace("Dr.", "").strip() or "?"})
        problems = []
        if not patient:
            problems.append(f"patient '{parsed.patient_name}' not found")
        if not drug:
            problems.append(f"drug '{parsed.drug_name}' is not in the knowledge base")
        if not prescriber:
            problems.append(f"prescriber '{parsed.prescriber_name}' not found")
        if problems:
            self.finding(order_id, "block", "intake", "Could not resolve order: " + "; ".join(problems) + ".")
            return {}

        rx_id = new_id("rx")
        add_prescription({
            "id": rx_id, "patient": patient[0]["id"], "prescriber": prescriber[0]["id"], "drug": drug[0]["id"],
            "route": parsed.route, "dose_mg": parsed.dose_mg, "concentration_pct": parsed.concentration_pct,
            "frequency_per_day": parsed.frequency_per_day, "duration_days": parsed.duration_days,
            "quantity": parsed.quantity, "notes": parsed.notes,
        })
        db.run("MATCH (o:Order {id: $o}) MATCH (rx:Prescription {id: $rx}) CREATE (o)-[:FILLS]->(rx)",
               {"o": order_id, "rx": rx_id})
        return self.context(order_id)
