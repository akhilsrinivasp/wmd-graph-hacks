"""Synthetic patients, prescribers and prescriptions for the demo.

All people here are fictional. No real patient data is used anywhere.
Each case is designed to exercise a different part of the graph.
"""

PRESCRIBERS = [
    {"id": "dr_okafor", "name": "Dr. Ada Okafor", "specialty": "Pediatrics", "npi": "DEMO-0001"},
    {"id": "dr_lindqvist", "name": "Dr. Erik Lindqvist", "specialty": "Internal medicine", "npi": "DEMO-0002"},
    {"id": "dr_raman", "name": "Dr. Priya Raman", "specialty": "Neurology", "npi": "DEMO-0003"},
]

PATIENTS = [
    {
        "id": "pt_maya", "name": "Maya Chen", "age_years": 4, "weight_kg": 16, "sex": "F",
        "conditions": ["hypertension"],
        "allergies": ["azo_dye"],
        "avoids": [],
        "takes": [],
        "story": "4-year-old who can't swallow tablets and is allergic to azo dyes.",
    },
    {
        "id": "pt_leo", "name": "Leo Martins", "age_years": 0.75, "weight_kg": 8.5, "sex": "M",
        "conditions": ["gerd"],
        "allergies": [],
        "avoids": [],
        "takes": [],
        "story": "9-month-old infant with reflux.",
    },
    {
        "id": "pt_aisha", "name": "Aisha Rahman", "age_years": 7, "weight_kg": 22, "sex": "F",
        "conditions": ["epilepsy", "hfi", "dysphagia"],
        "allergies": [],
        "avoids": [],
        "takes": [],
        "story": "7-year-old with epilepsy and hereditary fructose intolerance: sucrose and sorbitol vehicles are out.",
    },
    {
        "id": "pt_robert", "name": "Robert Hale", "age_years": 68, "weight_kg": 82, "sex": "M",
        "conditions": ["pah", "cad", "dysphagia"],
        "allergies": [],
        "avoids": [],
        "takes": ["isosorbide_mononitrate"],
        "story": "68-year-old with pulmonary hypertension, on a nitrate for angina, swallowing problems after a stroke.",
    },
    {
        "id": "pt_daniel", "name": "Daniel Okoro", "age_years": 55, "weight_kg": 90, "sex": "M",
        "conditions": ["osteoarthritis", "renal_impairment", "hypertension", "atrial_fibrillation"],
        "allergies": ["soy_derived"],
        "avoids": [],
        "takes": ["lisinopril", "warfarin"],
        "story": "55-year-old with knee arthritis, kidney disease, on warfarin and lisinopril, allergic to soy.",
    },
    {
        "id": "pt_sofia", "name": "Sofia Alvarez", "age_years": 6, "weight_kg": 20, "sex": "F",
        "conditions": ["giardiasis"],
        "allergies": ["penicillin"],
        "avoids": [],
        "takes": [],
        "story": "6-year-old with giardiasis; the prescription has a dosing error.",
    },
    {
        "id": "pt_ethan", "name": "Ethan Brooks", "age_years": 45, "weight_kg": 78, "sex": "M",
        "conditions": ["hypothyroidism", "lactose_intolerance"],
        "allergies": ["colorant"],
        "avoids": ["animal_derived"],
        "takes": [],
        "story": "45-year-old reacting to tablet dyes, lactose intolerant, vegetarian (no gelatin).",
    },
]

# Prescriptions. dose_mg is per administration (oral); concentration_pct for topicals.
PRESCRIPTIONS = [
    {"id": "rx_1001", "patient": "pt_maya", "prescriber": "dr_okafor", "drug": "amlodipine",
     "route": "oral", "dose_mg": 1.5, "frequency_per_day": 1, "duration_days": 30,
     "notes": "Cannot swallow tablets. Allergic to dyes."},
    {"id": "rx_1002", "patient": "pt_leo", "prescriber": "dr_okafor", "drug": "omeprazole",
     "route": "oral", "dose_mg": 8, "frequency_per_day": 1, "duration_days": 30,
     "notes": "Infant, needs liquid."},
    {"id": "rx_1003", "patient": "pt_aisha", "prescriber": "dr_raman", "drug": "gabapentin",
     "route": "oral", "dose_mg": 200, "frequency_per_day": 3, "duration_days": 30,
     "notes": "Hereditary fructose intolerance - no sugar/sorbitol."},
    {"id": "rx_1004", "patient": "pt_robert", "prescriber": "dr_lindqvist", "drug": "sildenafil",
     "route": "oral", "dose_mg": 20, "frequency_per_day": 3, "duration_days": 30,
     "notes": "Dysphagia post-stroke, needs liquid."},
    {"id": "rx_1005", "patient": "pt_daniel", "prescriber": "dr_lindqvist", "drug": "ketoprofen",
     "route": "topical", "concentration_pct": 10, "frequency_per_day": 3, "duration_days": 30,
     "quantity": 60, "notes": "Apply to right knee."},
    {"id": "rx_1006", "patient": "pt_sofia", "prescriber": "dr_okafor", "drug": "metronidazole",
     "route": "oral", "dose_mg": 500, "frequency_per_day": 3, "duration_days": 7,
     "notes": "Giardiasis."},
    {"id": "rx_1007", "patient": "pt_ethan", "prescriber": "dr_lindqvist", "drug": "levothyroxine",
     "route": "oral", "dose_mg": 0.1, "frequency_per_day": 1, "duration_days": 90,
     "notes": "Dye-free, lactose-free, no gelatin."},
]

# A free-text order used to demo the Claude-powered intake agent.
FREE_TEXT_EXAMPLE = (
    "Patient: Maya Chen. Rx from Dr. Okafor: amlodipine 1.5 mg by mouth once daily for 30 days. "
    "She can't swallow pills and reacts to food dyes. Please make a liquid."
)
