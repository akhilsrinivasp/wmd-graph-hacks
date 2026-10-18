"""Policy and regulation excerpts for graph-based retrieval (GraphRAG).

Short paraphrases with their source. Federal items are paraphrased from the
public documents named in `source`; plan items describe the synthetic demo
plans. Paraphrases are for the demo; always check the original text.
"""

POLICY_CHUNKS = [
    {"id": "pol_503a_rx", "source": "FD&C Act section 503A (FDA: Compounding Laws and Policies)",
     "url": "https://www.fda.gov/drugs/human-drug-compounding/compounding-laws-and-policies",
     "text": "A 503A pharmacy may compound a drug only on receipt of a valid prescription for an identified "
             "individual patient. Compounded drugs are exempt from FDA approval, CGMP and labeling-with-adequate-"
             "directions requirements only when all 503A conditions are met.",
     "mentions": ["compound"]},
    {"id": "pol_503a_copies", "source": "FD&C Act section 503A(b)(1)(D)",
     "url": "https://www.fda.gov/drugs/human-drug-compounding/compounding-laws-and-policies",
     "text": "A 503A pharmacy should not regularly or in inordinate amounts compound drugs that are essentially "
             "copies of a commercially available drug product. A change made for an identified patient, such as "
             "removing a dye the patient is allergic to or making a liquid for a patient who cannot swallow, "
             "should be documented on the prescription as the clinical reason.",
     "mentions": ["compound", "red_40", "oral_suspension"]},
    {"id": "pol_not_approved", "source": "FDA: Compounding and the FDA, Questions and Answers",
     "url": "https://www.fda.gov/drugs/human-drug-compounding/compounding-and-fda-questions-and-answers",
     "text": "Compounded drugs are not FDA-approved: FDA does not verify their safety, effectiveness or quality "
             "before they are marketed. They should be used only for patients whose medical needs cannot be met "
             "by an FDA-approved drug, for example an allergy to a dye or a child who needs a liquid.",
     "mentions": ["compound"]},
    {"id": "pol_503b", "source": "FD&C Act section 503B (Drug Quality and Security Act, 2013)",
     "url": "https://www.fda.gov/drugs/human-drug-compounding/compounding-laws-and-policies",
     "text": "Outsourcing facilities registered under 503B follow CGMP, are inspected by FDA on a risk-based "
             "schedule, and may compound without a patient-specific prescription (e.g. office stock for hospitals).",
     "mentions": ["compound"]},
    {"id": "pol_biologics", "source": "FDA: Compounding and the FDA, Questions and Answers",
     "url": "https://www.fda.gov/drugs/human-drug-compounding/compounding-and-fda-questions-and-answers",
     "text": "Biological products are not eligible for the 503A or 503B compounding exemptions.",
     "mentions": ["compound"]},
    {"id": "pol_usp795_bud", "source": "USP General Chapter <795> (nonsterile compounding), paraphrased",
     "url": "https://www.usp.org/compounding/general-chapter-795",
     "text": "Without a drug-specific stability study, USP <795> sets default beyond-use dates: non-aqueous "
             "solid forms such as capsules up to 180 days; preserved aqueous forms 35 days; unpreserved aqueous "
             "forms 14 days refrigerated. A published stability study can support a longer date.",
     "mentions": ["capsule", "oral_suspension", "oral_solution"]},
    {"id": "pol_partd_compound", "source": "CMS Medicare Prescription Drug Benefit Manual, Chapter 6, paraphrased",
     "url": "https://www.cms.gov/medicare/prescription-drug-coverage/prescriptiondrugcovcontra/downloads/part-d-benefits-manual-chapter-6.pdf",
     "text": "Medicare Part D covers a compounded prescription only to the extent its ingredients are Part D drugs. "
             "Bulk powders and inactive ingredients are generally not Part D drugs, so plans may pay for only part "
             "of a compound or require prior authorization.",
     "mentions": ["plan_silver_d", "compound"]},
    {"id": "pol_acme_compound", "source": "Acme Health PPO formulary rules (synthetic demo plan)",
     "url": "",
     "text": "Acme Health PPO covers compounded prescriptions only with prior authorization showing that no covered "
             "commercial product is suitable for the patient, for example because every covered product contains "
             "an ingredient the patient is allergic to.",
     "mentions": ["plan_acme_ppo", "compound"]},
    {"id": "pol_acme_forms", "source": "Acme Health PPO formulary rules (synthetic demo plan)",
     "url": "",
     "text": "Acme Health PPO lists amlodipine oral suspension (Katerzia) as the preferred liquid; amlodipine oral "
             "solution is non-formulary and claims for it are denied. Gabapentin oral solution is non-formulary "
             "while capsules and tablets are covered. Levothyroxine liquids and capsules need step therapy: "
             "tablets first unless a reason is documented.",
     "mentions": ["plan_acme_ppo", "amlodipine", "gabapentin", "levothyroxine", "oral_solution", "oral_suspension", "tablet", "capsule"]},
    {"id": "pol_silver_alt", "source": "Silver Star Medicare Part D formulary rules (synthetic demo plan)",
     "url": "",
     "text": "Silver Star Part D does not list ketoprofen. Prescription diclofenac 1% topical gel is covered on tier 2 "
             "without prior authorization and is the preferred topical NSAID.",
     "mentions": ["plan_silver_d", "ketoprofen", "diclofenac", "transdermal_gel"]},
    {"id": "pol_medicaid_compound", "source": "State Medicaid pharmacy rules (synthetic demo plan)",
     "url": "",
     "text": "State Medicaid covers compounded prescriptions for patients under 21 who cannot use a commercial "
             "dosage form without prior authorization; adults need prior authorization. Brand omeprazole and "
             "metronidazole suspensions need prior authorization.",
     "mentions": ["plan_state_medicaid", "omeprazole", "metronidazole", "compound"]},
    {"id": "pol_pa_general", "source": "Prior authorization practice (general)",
     "url": "",
     "text": "A prior authorization request should state the diagnosis, the prescribed drug and dose, which covered "
             "alternatives were tried or why they are unsuitable (allergy, inability to swallow, intolerance), "
             "and the prescriber's details. Missing reasons are the most common cause of denial.",
     "mentions": []},
]
