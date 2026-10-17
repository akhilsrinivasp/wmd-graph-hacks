"""History agent: builds the patient context the other agents rely on.

It writes derived facts back into the graph (age-based conditions such as
"Young child") so later queries can treat them like any other condition, and
it recalls what happened on the patient's earlier orders.
"""
from compounder import db
from compounder import queries as Q
from compounder.agents.base import Agent


def age_conditions(age_years: float) -> list[str]:
    ids = []
    if age_years < 1 / 12:
        ids.append("neonate")
    if age_years < 6:
        ids.append("young_child")
    if age_years >= 65:
        ids.append("older_adult")
    return ids


class HistoryAgent(Agent):
    name = "History"
    handles_status = "INTAKE_DONE"
    next_status = "CONTEXT_READY"

    def run(self, order_id: str) -> None:
        ctx = self.context(order_id)
        patient = ctx["patient"]

        derived = age_conditions(patient.get("age_years", 30))
        db.run(Q.SET_DERIVED_CONDITIONS, {"patient_id": patient["id"], "condition_ids": derived})
        if derived:
            self.log(order_id, "derive_facts",
                     f"Age {patient['age_years']} y: added derived condition(s) {', '.join(derived)}.",
                     used_ids=[patient["id"], *derived])

        prof = db.run(Q.PATIENT_PROFILE, {"patient_id": patient["id"]})[0]
        conditions = [c["name"] for c in prof["conditions"] if c.get("name")]
        parts = [
            f"{patient['name']}, {patient['age_years']} y, {patient['weight_kg']} kg.",
            f"Conditions: {', '.join(conditions) or 'none'}.",
            f"Allergies: {', '.join(prof['allergies']) or 'none'}.",
        ]
        if prof["avoids"]:
            parts.append(f"Avoids: {', '.join(prof['avoids'])}.")
        parts.append(f"Current meds: {', '.join(prof['meds']) or 'none'}.")
        self.log(order_id, "load_profile", " ".join(parts), used_ids=[patient["id"]])

        # Memory from earlier orders
        history = db.run(Q.PATIENT_ORDER_HISTORY, {"patient_id": patient["id"], "order_id": order_id})
        if history or prof["reactions"] or prof["tolerated"]:
            mem = []
            if history:
                mem.append(f"{len(history)} earlier order(s): " +
                           "; ".join(f"{h['drug']} ({h['status'].lower()})" for h in history[:5]))
            if prof["tolerated"]:
                mem.append(f"previously tolerated: {', '.join(prof['tolerated'])}")
            if prof["reactions"]:
                mem.append(f"past reactions to: {', '.join(prof['reactions'])}")
            self.log(order_id, "recall_memory", "; ".join(mem) + ".", used_ids=[patient["id"]])

        if not patient.get("weight_kg"):
            self.finding(order_id, "warn", "history", "No weight on file; weight-based dose check is not possible.")
        self.set_status(order_id, self.next_status)
