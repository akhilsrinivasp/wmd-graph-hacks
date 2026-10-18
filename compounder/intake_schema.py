"""Structured patient record: the format patient data enters the graph in.

A record is validated with Pydantic, every free-text name (allergy,
condition, medicine, plan) is resolved to a graph node, and details such as
allergy reaction and severity are stored on the relationship.
"""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field

from compounder import db
from compounder.seed.loader import add_patient, add_prescription, create_order


class Allergy(BaseModel):
    substance: str = Field(description="Drug, drug class, ingredient or ingredient group, e.g. 'penicillin', 'azo dye'")
    reaction: str = ""
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"


class HistoryItem(BaseModel):
    condition: str
    since: str = ""
    notes: str = ""


class Medication(BaseModel):
    drug: str
    dose: str = ""


class Insurance(BaseModel):
    plan: str = Field(description="Plan id or name")
    member_id: str = ""


class PrescriptionIn(BaseModel):
    prescriber: str
    drug: str
    route: Literal["oral", "topical"] = "oral"
    dose_mg: Optional[float] = None
    concentration_pct: Optional[float] = None
    frequency_per_day: int = 1
    duration_days: int = 30
    quantity: Optional[float] = None
    notes: str = ""


class PatientRecord(BaseModel):
    name: str
    age_years: float
    weight_kg: float
    sex: Literal["F", "M", "X"] = "X"
    allergies: list[Allergy] = []
    history: list[HistoryItem] = []
    medications: list[Medication] = []
    dietary_restrictions: list[str] = Field(default=[], description="e.g. 'animal-derived' (vegetarian)")
    insurance: Optional[Insurance] = None
    prescription: Optional[PrescriptionIn] = None


def resolve(name: str, labels: list[str]) -> Optional[str]:
    """Match a free-text name to a node id by id, name, alias or partial name."""
    key = name.strip().lower().replace(" ", "_")
    where = " OR ".join(f"n:{l}" for l in labels)
    rows = db.run(
        f"""MATCH (n) WHERE ({where}) AND (
              n.id = $key OR toLower(n.name) = $name
              OR (n.aliases IS NOT NULL AND $name IN [a IN n.aliases | toLower(a)])
              OR toLower(n.name) CONTAINS $name)
            RETURN n.id AS id, size(n.name) AS len ORDER BY len LIMIT 1""",
        {"key": key, "name": name.strip().lower()})
    return rows[0]["id"] if rows else None


def import_record(rec: PatientRecord) -> dict:
    """Write a validated record to the graph. Returns ids plus anything that could not be matched."""
    unmatched = []

    def match(name, labels):
        rid = resolve(name, labels)
        if not rid:
            unmatched.append(name)
        return rid

    allergies = []
    for a in rec.allergies:
        rid = match(a.substance, ["Drug", "DrugClass", "Excipient", "ExcipientGroup"])
        if rid:
            allergies.append({"id": rid, "reaction": a.reaction, "severity": a.severity})
    conditions = []
    for h in rec.history:
        rid = match(h.condition, ["Condition"])
        if rid:
            conditions.append({"id": rid, "since": h.since, "notes": h.notes})
    takes = [{"id": rid, "dose": m.dose} for m in rec.medications
             if (rid := match(m.drug, ["Drug"]))]
    avoids = [rid for d in rec.dietary_restrictions if (rid := match(d, ["ExcipientGroup", "Excipient"]))]
    insurance = None
    if rec.insurance:
        plan_id = match(rec.insurance.plan, ["InsurancePlan"])
        if plan_id:
            insurance = {"plan_id": plan_id, "member_id": rec.insurance.member_id}

    pid = f"pt_{uuid.uuid4().hex[:8]}"
    add_patient({"id": pid, "name": rec.name, "age_years": rec.age_years, "weight_kg": rec.weight_kg,
                 "sex": rec.sex, "conditions": conditions, "allergies": allergies, "takes": takes,
                 "avoids": avoids, "insurance": insurance, "story": "Imported structured record."})
    out = {"patient_id": pid, "unmatched": unmatched, "order_id": None}

    if rec.prescription:
        p = rec.prescription
        drug_id = match(p.drug, ["Drug"])
        doc_id = match(p.prescriber.replace("Dr.", "").strip(), ["Prescriber"])
        if drug_id and doc_id:
            rx_id = f"rx_{uuid.uuid4().hex[:8]}"
            add_prescription({"id": rx_id, "patient": pid, "prescriber": doc_id, "drug": drug_id,
                              "route": p.route, "dose_mg": p.dose_mg, "concentration_pct": p.concentration_pct,
                              "frequency_per_day": p.frequency_per_day, "duration_days": p.duration_days,
                              "quantity": p.quantity, "notes": p.notes})
            out["order_id"] = create_order(rx_id, source="structured record")
    return out
