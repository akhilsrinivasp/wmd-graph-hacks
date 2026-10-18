"""Synthetic insurance plans and formularies.

SYNTHETIC DATA. Plan names, tiers and copays are made up, but the patterns are
real ones pharmacists deal with every day:
  - coverage is set per drug AND dosage form (tablet covered, liquid denied, or the reverse)
  - specific products are non-formulary while an equivalent brand is preferred
  - step therapy / prior authorization (PA) for costlier forms
  - each plan has its own rule for compounded drugs
  - a covered therapeutic alternative can beat an uncovered prescribed drug
"""

PLANS = [
    {"id": "plan_acme_ppo", "name": "Acme Health PPO", "type": "commercial",
     "compound_covered": True, "compound_pa": True, "compound_copay": 30,
     "compound_rule": "Compounded prescriptions need prior authorization showing that no covered "
                      "commercial product is suitable for the patient."},
    {"id": "plan_silver_d", "name": "Silver Star Medicare Part D", "type": "medicare_part_d",
     "compound_covered": True, "compound_pa": True, "compound_copay": 47,
     "compound_rule": "Part D pays for a compound only for ingredients that are themselves Part D drugs; "
                      "bulk powders and inactive bases are not covered. PA required."},
    {"id": "plan_state_medicaid", "name": "State Medicaid (demo)", "type": "medicaid",
     "compound_covered": True, "compound_pa": False, "compound_copay": 1,
     "compound_rule": "Compounds for patients under 21 who cannot use a commercial form are covered "
                      "without PA; adults need PA."},
]

# (plan, drug, form, status, tier, copay_usd, prior_auth, note)
# status: covered | excluded
FORMULARY = [
    # Acme PPO
    ("plan_acme_ppo", "amlodipine", "tablet", "covered", 1, 5, False, ""),
    ("plan_acme_ppo", "amlodipine", "oral_suspension", "covered", 2, 15, False, "Katerzia is the preferred liquid."),
    ("plan_acme_ppo", "amlodipine", "oral_solution", "excluded", None, None, False,
     "Non-formulary. Plan will reimburse the oral suspension instead."),
    ("plan_acme_ppo", "gabapentin", "capsule", "covered", 1, 5, False, ""),
    ("plan_acme_ppo", "gabapentin", "tablet", "covered", 1, 5, False, ""),
    ("plan_acme_ppo", "gabapentin", "oral_solution", "excluded", None, None, False,
     "Non-formulary liquid. Capsules are covered."),
    ("plan_acme_ppo", "levothyroxine", "tablet", "covered", 1, 0, False, ""),
    ("plan_acme_ppo", "levothyroxine", "oral_solution", "covered", 3, 75, True,
     "Step therapy: must try tablets first unless there is a documented reason."),
    ("plan_acme_ppo", "levothyroxine", "capsule", "covered", 3, 75, True, "Step therapy: tablets first."),
    ("plan_acme_ppo", "diclofenac", "transdermal_gel", "covered", 2, 10, False, "Diclofenac 1% gel."),
    ("plan_acme_ppo", "ketoprofen", "capsule", "covered", 2, 12, False, ""),
    # Silver Star Medicare Part D
    ("plan_silver_d", "sildenafil", "tablet", "covered", 4, 45, True, "PA: PAH diagnosis required."),
    ("plan_silver_d", "sildenafil", "oral_suspension", "covered", 5, 95, True, "PA: PAH diagnosis and dysphagia."),
    ("plan_silver_d", "diclofenac", "transdermal_gel", "covered", 2, 9, False, "Rx diclofenac 1% gel."),
    ("plan_silver_d", "ketoprofen", "capsule", "excluded", None, None, False, "Not on formulary."),
    ("plan_silver_d", "lidocaine", "transdermal_gel", "covered", 3, 35, True, ""),
    # State Medicaid
    ("plan_state_medicaid", "omeprazole", "capsule", "covered", 1, 1, False, ""),
    ("plan_state_medicaid", "omeprazole", "oral_suspension", "covered", 2, 3, True,
     "Brand packets need PA; compounded suspension preferred for infants."),
    ("plan_state_medicaid", "metronidazole", "tablet", "covered", 1, 1, False, ""),
    ("plan_state_medicaid", "metronidazole", "oral_suspension", "covered", 2, 3, True, "Brand suspension needs PA."),
    ("plan_state_medicaid", "amlodipine", "tablet", "covered", 1, 1, False, ""),
]

# Covered alternatives a pharmacist might suggest to the prescriber.
THERAPEUTIC_ALTERNATIVES = [
    ("ketoprofen", "diclofenac", "Both topical NSAIDs for joint pain; diclofenac 1% gel is FDA-approved and widely covered."),
]

# Which plan each demo patient has
PATIENT_PLANS = {
    "pt_maya": ("plan_acme_ppo", "ACM-104-22"),
    "pt_leo": ("plan_state_medicaid", "MCD-55-019"),
    "pt_aisha": ("plan_acme_ppo", "ACM-208-71"),
    "pt_robert": ("plan_silver_d", "SSD-771-03"),
    "pt_daniel": ("plan_silver_d", "SSD-430-88"),
    "pt_sofia": ("plan_state_medicaid", "MCD-77-412"),
    "pt_ethan": ("plan_acme_ppo", "ACM-919-05"),
}
