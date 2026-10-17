"""Curated pharmacology knowledge base for the demo.

DEMO DATA ONLY. Values are taken from common pediatric/adult references and
published compounding stability studies, simplified for a hackathon. They are
NOT verified for clinical use. Every formulation the agents produce must be
checked by a licensed pharmacist.

Everything here is loaded into FalkorDB by `compounder.seed.loader`. The agents
never read these Python structures directly; they only query the graph.
"""

# ---------------------------------------------------------------------------
# Drug classes. Drugs and classes form one IS_A hierarchy, so a single
# variable-length path query covers "is this drug a kind of X".
# ---------------------------------------------------------------------------
DRUG_CLASSES = [
    # (id, name, parent_id)
    ("beta_lactam", "Beta-lactam antibiotic", None),
    ("penicillin", "Penicillin", "beta_lactam"),
    ("aminopenicillin", "Aminopenicillin", "penicillin"),
    ("cephalosporin", "Cephalosporin", "beta_lactam"),
    ("nitroimidazole", "Nitroimidazole antibiotic", None),
    ("ppi", "Proton pump inhibitor", None),
    ("ccb", "Calcium channel blocker", None),
    ("acei", "ACE inhibitor", None),
    ("k_sparing", "Potassium-sparing diuretic", None),
    ("thiazide", "Thiazide diuretic", None),
    ("pde5", "PDE5 inhibitor", None),
    ("nitrate", "Nitrate vasodilator", None),
    ("gabapentinoid", "Gabapentinoid", None),
    ("gaba_b", "GABA-B agonist (muscle relaxant)", None),
    ("cns_depressant", "CNS depressant", None),
    ("nsaid", "NSAID", None),
    ("vka", "Vitamin K antagonist anticoagulant", None),
    ("antiplatelet_p2y12", "P2Y12 antiplatelet", None),
    ("k_supplement", "Potassium supplement", None),
    ("bile_acid", "Bile acid", None),
    ("local_anesthetic", "Amide local anesthetic", None),
    ("thyroid", "Thyroid hormone", None),
]

# gabapentinoids and GABA-B agonists are both CNS depressants
EXTRA_CLASS_LINKS = [("gabapentinoid", "cns_depressant"), ("gaba_b", "cns_depressant")]

DRUGS = [
    # id, name, class_id, aliases (brand names etc.)
    ("omeprazole", "Omeprazole", "ppi", ["Prilosec"]),
    ("lansoprazole", "Lansoprazole", "ppi", ["Prevacid"]),
    ("amlodipine", "Amlodipine", "ccb", ["Norvasc", "Katerzia"]),
    ("enalapril", "Enalapril", "acei", ["Vasotec", "Epaned"]),
    ("lisinopril", "Lisinopril", "acei", ["Zestril", "Prinivil"]),
    ("spironolactone", "Spironolactone", "k_sparing", ["Aldactone", "CaroSpir"]),
    ("hydrochlorothiazide", "Hydrochlorothiazide", "thiazide", ["HCTZ"]),
    ("sildenafil", "Sildenafil", "pde5", ["Revatio", "Viagra"]),
    ("isosorbide_mononitrate", "Isosorbide mononitrate", "nitrate", ["Imdur"]),
    ("nitroglycerin", "Nitroglycerin", "nitrate", ["Nitrostat"]),
    ("baclofen", "Baclofen", "gaba_b", ["Lioresal", "Ozobax"]),
    ("gabapentin", "Gabapentin", "gabapentinoid", ["Neurontin"]),
    ("metronidazole", "Metronidazole", "nitroimidazole", ["Flagyl"]),
    ("ursodiol", "Ursodiol", "bile_acid", ["Actigall"]),
    ("levothyroxine", "Levothyroxine", "thyroid", ["Synthroid", "Levoxyl"]),
    ("ketoprofen", "Ketoprofen", "nsaid", []),
    ("diclofenac", "Diclofenac", "nsaid", ["Voltaren"]),
    ("ibuprofen", "Ibuprofen", "nsaid", ["Advil", "Motrin"]),
    ("lidocaine", "Lidocaine", "local_anesthetic", ["Xylocaine"]),
    ("amoxicillin", "Amoxicillin", "aminopenicillin", ["Amoxil"]),
    ("cephalexin", "Cephalexin", "cephalosporin", ["Keflex"]),
    ("warfarin", "Warfarin", "vka", ["Coumadin", "Jantoven"]),
    ("clopidogrel", "Clopidogrel", "antiplatelet_p2y12", ["Plavix"]),
    ("potassium_chloride", "Potassium chloride", "k_supplement", ["K-Dur", "Klor-Con"]),
]

# ---------------------------------------------------------------------------
# Interactions. Endpoints can be drugs, drug classes or excipients; queries walk
# IS_A paths so a class-level rule applies to every drug in the class.
# severity: block (do not dispense without prescriber change) | warn | info
# ---------------------------------------------------------------------------
INTERACTIONS = [
    ("pde5", "nitrate", "block", "Severe, potentially fatal hypotension. Concomitant use is contraindicated."),
    ("acei", "k_sparing", "warn", "Additive risk of hyperkalemia. Monitor potassium."),
    ("acei", "k_supplement", "warn", "Risk of hyperkalemia. Monitor potassium."),
    ("metronidazole", "warfarin", "warn", "Metronidazole raises warfarin levels; INR may rise and bleeding risk increases."),
    ("metronidazole", "ethanol", "block", "Disulfiram-like reaction (flushing, vomiting, tachycardia)."),
    ("nsaid", "vka", "warn", "Increased bleeding risk."),
    ("nsaid", "acei", "info", "NSAIDs can blunt the antihypertensive effect and stress kidney function."),
    ("omeprazole", "clopidogrel", "warn", "Omeprazole reduces activation of clopidogrel; consider another acid suppressant."),
    ("cns_depressant", "cns_depressant", "info", "Additive sedation / CNS depression."),
]

# Allergy cross-reactivity between classes (warn, not block).
CROSS_REACTIVITY = [
    ("penicillin", "cephalosporin", "warn",
     "Low (about 1-2%) but real cross-reactivity, higher with similar side chains."),
]

# ---------------------------------------------------------------------------
# Conditions (patient history and facts the history agent derives from age).
# ---------------------------------------------------------------------------
CONDITIONS = [
    ("renal_impairment", "Renal impairment"),
    ("hepatic_impairment", "Hepatic impairment"),
    ("pregnancy", "Pregnancy"),
    ("hyperkalemia", "Hyperkalemia"),
    ("diabetes", "Diabetes mellitus"),
    ("pku", "Phenylketonuria"),
    ("hfi", "Hereditary fructose intolerance"),
    ("lactose_intolerance", "Lactose intolerance"),
    ("celiac", "Celiac disease"),
    ("alcohol_use_disorder", "Alcohol use disorder"),
    ("dysphagia", "Dysphagia (difficulty swallowing)"),
    ("hypertension", "Hypertension"),
    ("gerd", "Gastroesophageal reflux"),
    ("pah", "Pulmonary arterial hypertension"),
    ("epilepsy", "Epilepsy"),
    ("osteoarthritis", "Osteoarthritis"),
    ("giardiasis", "Giardiasis"),
    ("hypothyroidism", "Hypothyroidism"),
    ("spasticity", "Spasticity"),
    ("heart_failure", "Heart failure"),
    ("cad", "Coronary artery disease"),
    ("atrial_fibrillation", "Atrial fibrillation"),
    # Derived from age by the history agent
    ("neonate", "Neonate (< 1 month)"),
    ("young_child", "Young child (< 6 years)"),
    ("older_adult", "Older adult (65+)"),
]

# Drug (or class) cautions in conditions.
DRUG_CAUTIONS = [
    ("acei", "pregnancy", "block", "Fetal toxicity (boxed warning). Do not use in pregnancy."),
    ("spironolactone", "hyperkalemia", "block", "Contraindicated in hyperkalemia."),
    ("spironolactone", "renal_impairment", "warn", "Higher hyperkalemia risk in renal impairment."),
    ("acei", "hyperkalemia", "warn", "May worsen hyperkalemia."),
    ("gabapentin", "renal_impairment", "warn", "Renally cleared. Dose must be reduced for low CrCl."),
    ("baclofen", "renal_impairment", "warn", "Renally cleared. Risk of toxicity; reduce dose."),
    ("nsaid", "renal_impairment", "warn", "NSAIDs can worsen kidney function (lower with topical use)."),
    ("metronidazole", "hepatic_impairment", "warn", "Reduce dose in severe hepatic impairment."),
    ("sildenafil", "hepatic_impairment", "warn", "Reduced clearance in hepatic impairment."),
]

# Conditions that call for a particular dosage form.
CONDITION_PREFERS_FORM = [
    ("dysphagia", "oral_suspension"), ("dysphagia", "oral_solution"),
    ("young_child", "oral_suspension"), ("young_child", "oral_solution"),
    ("neonate", "oral_suspension"), ("neonate", "oral_solution"),
]

# ---------------------------------------------------------------------------
# Excipients (inactive ingredients) and their IS_A taxonomy.
# aliases are the strings used to recognise them in FDA label text.
# ---------------------------------------------------------------------------
EXCIPIENT_GROUPS = [
    # (id, name, parent_id)
    ("colorant", "Colorant (any dye)", None),
    ("azo_dye", "Azo dye", "colorant"),
    ("sugar", "Sugar", None),
    ("fructose_source", "Fructose source", None),
    ("sugar_alcohol", "Sugar alcohol", None),
    ("artificial_sweetener", "Artificial sweetener", None),
    ("phenylalanine_source", "Phenylalanine source", None),
    ("preservative", "Preservative", None),
    ("paraben", "Paraben", "preservative"),
    ("alcohol_solvent", "Alcohol (solvent)", None),
    ("glycol", "Glycol solvent", None),
    ("starch", "Starch", None),
    ("gluten_source", "Gluten source", None),
    ("milk_derived", "Milk-derived", None),
    ("animal_derived", "Animal-derived", None),
    ("soy_derived", "Soy-derived", None),
    ("peanut_derived", "Peanut-derived", None),
]

EXCIPIENTS = [
    # (id, name, [parent group ids], [label aliases])
    ("red_40", "FD&C Red No. 40", ["azo_dye"], ["RED NO. 40", "RED #40", "RED 40", "ALLURA RED"]),
    ("yellow_5", "FD&C Yellow No. 5 (tartrazine)", ["azo_dye"], ["YELLOW NO. 5", "YELLOW #5", "TARTRAZINE"]),
    ("yellow_6", "FD&C Yellow No. 6", ["azo_dye"], ["YELLOW NO. 6", "YELLOW #6", "SUNSET YELLOW"]),
    ("blue_1", "FD&C Blue No. 1", ["colorant"], ["BLUE NO. 1", "BLUE #1", "BRILLIANT BLUE"]),
    ("blue_2", "FD&C Blue No. 2", ["colorant"], ["BLUE NO. 2", "BLUE #2", "INDIGO CARMINE", "INDIGOTINE"]),
    ("dc_yellow_10", "D&C Yellow No. 10", ["colorant"], ["D&C YELLOW NO. 10", "D&C YELLOW #10", "QUINOLINE YELLOW"]),
    ("dc_red_27", "D&C Red No. 27", ["colorant"], ["D&C RED NO. 27"]),
    ("sucrose", "Sucrose", ["sugar", "fructose_source"], ["SUCROSE"]),
    ("lactose", "Lactose", ["sugar", "milk_derived"], ["LACTOSE"]),
    ("sorbitol", "Sorbitol", ["sugar_alcohol", "fructose_source"], ["SORBITOL"]),
    ("xylitol", "Xylitol", ["sugar_alcohol"], ["XYLITOL"]),
    ("mannitol", "Mannitol", ["sugar_alcohol"], ["MANNITOL"]),
    ("aspartame", "Aspartame", ["artificial_sweetener", "phenylalanine_source"], ["ASPARTAME"]),
    ("saccharin", "Sodium saccharin", ["artificial_sweetener"], ["SACCHARIN"]),
    ("sucralose", "Sucralose", ["artificial_sweetener"], ["SUCRALOSE"]),
    ("methylparaben", "Methylparaben", ["paraben"], ["METHYLPARABEN"]),
    ("propylparaben", "Propylparaben", ["paraben"], ["PROPYLPARABEN"]),
    ("sodium_benzoate", "Sodium benzoate", ["preservative"], ["SODIUM BENZOATE"]),
    ("potassium_sorbate", "Potassium sorbate", ["preservative"], ["POTASSIUM SORBATE"]),
    ("benzyl_alcohol", "Benzyl alcohol", ["preservative", "alcohol_solvent"], ["BENZYL ALCOHOL"]),
    ("ethanol", "Ethanol", ["alcohol_solvent"], ["DEHYDRATED ALCOHOL", "ETHYL ALCOHOL", "ETHANOL"]),
    ("propylene_glycol", "Propylene glycol", ["glycol"], ["PROPYLENE GLYCOL"]),
    ("corn_starch", "Corn starch (modified)", ["starch"], ["STARCH, CORN", "CORN STARCH", "MAIZE STARCH"]),
    ("wheat_starch", "Wheat starch", ["starch", "gluten_source"], ["STARCH, WHEAT", "WHEAT STARCH"]),
    ("gelatin", "Gelatin", ["animal_derived"], ["GELATIN"]),
    ("soy_lecithin", "Soy lecithin", ["soy_derived"], ["LECITHIN, SOYBEAN", "SOY LECITHIN", "SOYBEAN LECITHIN"]),
    ("peanut_oil", "Peanut oil", ["peanut_derived"], ["PEANUT OIL", "ARACHIS OIL"]),
    # Common, generally non-problematic excipients
    ("mcc", "Microcrystalline cellulose", [], ["MICROCRYSTALLINE CELLULOSE", "CELLULOSE, MICROCRYSTALLINE"]),
    ("cmc", "Carboxymethylcellulose sodium", [], ["CARBOXYMETHYLCELLULOSE"]),
    ("xanthan", "Xanthan gum", [], ["XANTHAN GUM"]),
    ("carrageenan", "Carrageenan", [], ["CARRAGEENAN"]),
    ("glycerin", "Glycerin", [], ["GLYCERIN"]),
    ("citric_acid", "Citric acid", [], ["CITRIC ACID"]),
    ("sodium_citrate", "Sodium citrate", [], ["SODIUM CITRATE"]),
    ("sodium_bicarbonate", "Sodium bicarbonate", [], ["SODIUM BICARBONATE"]),
    ("water", "Purified water", [], []),
    ("magnesium_stearate", "Magnesium stearate", [], ["MAGNESIUM STEARATE"]),
    ("hypromellose", "Hypromellose", [], ["HYPROMELLOSE"]),
    ("poloxamer", "Poloxamer 407", [], ["POLOXAMER"]),
    ("isopropyl_palmitate", "Isopropyl palmitate", [], ["ISOPROPYL PALMITATE"]),
    ("white_petrolatum", "White petrolatum", [], ["PETROLATUM"]),
    ("stearyl_alcohol", "Stearyl alcohol", [], ["STEARYL ALCOHOL"]),
    ("sodium_lauryl_sulfate", "Sodium lauryl sulfate", [], ["SODIUM LAURYL SULFATE"]),
    ("mineral_oil", "Mineral oil", [], ["MINERAL OIL"]),
]

# Excipients (or groups) that matter for a condition.
# block = exclude any base containing it; warn = allowed but flagged.
EXCIPIENT_AVOID_IN = [
    ("phenylalanine_source", "pku", "block", "Aspartame is a source of phenylalanine."),
    ("fructose_source", "hfi", "block", "Sucrose and sorbitol are metabolised to fructose."),
    ("gluten_source", "celiac", "block", "Contains gluten."),
    ("lactose", "lactose_intolerance", "warn", "Contains lactose (small amounts are often tolerated)."),
    ("sugar", "diabetes", "warn", "Sugar-containing vehicle; prefer sugar-free."),
    ("alcohol_solvent", "alcohol_use_disorder", "block", "Contains alcohol."),
    ("benzyl_alcohol", "neonate", "block", "Benzyl alcohol is linked to 'gasping syndrome' in neonates."),
    ("propylene_glycol", "neonate", "warn", "Neonates clear propylene glycol poorly."),
    ("ethanol", "young_child", "warn", "Avoid alcohol-containing vehicles in young children where possible."),
]

# ---------------------------------------------------------------------------
# Dosage forms and compounding bases (vehicles).
# Base compositions are generic representative formulas, not specific brands.
# aqueous / preserved drive the USP <795> default beyond-use date.
# ---------------------------------------------------------------------------
DOSAGE_FORMS = [
    # id, name, route, liquid
    ("oral_suspension", "Oral suspension", "oral", True),
    ("oral_solution", "Oral solution", "oral", True),
    ("capsule", "Capsule", "oral", False),
    ("tablet", "Tablet", "oral", False),
    ("transdermal_gel", "Transdermal gel", "topical", False),
    ("topical_ointment", "Topical ointment", "topical", False),
    ("topical_cream", "Topical cream", "topical", False),
]

BASES = [
    {
        "id": "susp_sucrose",
        "name": "Suspending vehicle + sucrose syrup (1:1)",
        "form": "oral_suspension", "aqueous": True, "preserved": True,
        "contains": ["water", "mcc", "cmc", "xanthan", "carrageenan", "sucrose", "glycerin",
                     "sorbitol", "citric_acid", "methylparaben", "potassium_sorbate"],
    },
    {
        "id": "susp_sugar_free",
        "name": "Sugar-free suspending vehicle (1:1)",
        "form": "oral_suspension", "aqueous": True, "preserved": True,
        "contains": ["water", "mcc", "cmc", "xanthan", "carrageenan", "glycerin", "sorbitol",
                     "saccharin", "citric_acid", "methylparaben", "propylparaben", "potassium_sorbate"],
    },
    {
        "id": "susp_starch_sf",
        "name": "Starch-based sugar-free suspending base (paraben-free)",
        "form": "oral_suspension", "aqueous": True, "preserved": True,
        "contains": ["water", "corn_starch", "sucralose", "citric_acid", "sodium_citrate", "sodium_benzoate"],
    },
    {
        "id": "bicarb_84",
        "name": "Sodium bicarbonate 8.4% vehicle",
        "form": "oral_suspension", "aqueous": True, "preserved": False,
        "contains": ["water", "sodium_bicarbonate"],
    },
    {
        "id": "syrup_aspartame",
        "name": "Sugar-free flavored syrup (aspartame)",
        "form": "oral_solution", "aqueous": True, "preserved": True,
        "contains": ["water", "glycerin", "aspartame", "xanthan", "citric_acid", "sodium_benzoate", "red_40"],
    },
    {
        "id": "elixir_hydroalcoholic",
        "name": "Hydroalcoholic elixir vehicle",
        "form": "oral_solution", "aqueous": True, "preserved": True,
        "contains": ["water", "ethanol", "glycerin", "sucrose", "propylene_glycol"],
    },
    {
        "id": "cap_mcc_hpmc",
        "name": "Microcrystalline cellulose fill, hypromellose (vegetarian) capsule",
        "form": "capsule", "aqueous": False, "preserved": False,
        "contains": ["mcc", "hypromellose"],
    },
    {
        "id": "cap_lactose_gelatin",
        "name": "Lactose fill, gelatin capsule",
        "form": "capsule", "aqueous": False, "preserved": False,
        "contains": ["lactose", "gelatin"],
    },
    {
        "id": "cap_mcc_gelatin",
        "name": "Microcrystalline cellulose fill, gelatin capsule",
        "form": "capsule", "aqueous": False, "preserved": False,
        "contains": ["mcc", "gelatin"],
    },
    {
        "id": "plo_gel",
        "name": "Pluronic lecithin organogel (PLO)",
        "form": "transdermal_gel", "aqueous": True, "preserved": True,
        "contains": ["soy_lecithin", "isopropyl_palmitate", "poloxamer", "water", "potassium_sorbate"],
    },
    {
        "id": "hydrophilic_ointment",
        "name": "Hydrophilic ointment base",
        "form": "topical_ointment", "aqueous": True, "preserved": True,
        "contains": ["white_petrolatum", "stearyl_alcohol", "propylene_glycol", "sodium_lauryl_sulfate",
                     "methylparaben", "propylparaben", "water"],
    },
    {
        "id": "anhydrous_petrolatum",
        "name": "Anhydrous petrolatum base",
        "form": "topical_ointment", "aqueous": False, "preserved": False,
        "contains": ["white_petrolatum", "mineral_oil"],
    },
]

# USP <795> default beyond-use dates (days) when no drug-specific stability
# study exists: keyed by (aqueous, preserved).
USP_795_DEFAULT_BUD = {
    (False, False): 180,   # non-aqueous solid (e.g. capsules)
    (False, True): 180,
    (True, True): 35,      # preserved aqueous
    (True, False): 14,     # unpreserved aqueous, refrigerated
}

# Drug stability in a base. conc is the standard concentration for liquids
# (mg/mL). For capsules and topicals conc is None: strength is taken from the
# prescription. bud_days None means "no specific study, use USP <795> default".
STABILITY = [
    # drug, base, conc mg/mL, bud_days, storage, reference
    ("omeprazole", "bicarb_84", 2.0, 30, "refrigerate", "Published stability study, 2 mg/mL in 8.4% sodium bicarbonate"),
    ("lansoprazole", "bicarb_84", 3.0, 14, "refrigerate", "Published stability study, 3 mg/mL in 8.4% sodium bicarbonate"),
    ("amlodipine", "susp_sucrose", 1.0, 90, "refrigerate", "Published stability study, 1 mg/mL in 1:1 suspending vehicle"),
    ("amlodipine", "susp_sugar_free", 1.0, 90, "refrigerate", "Published stability study, 1 mg/mL in sugar-free 1:1 vehicle"),
    ("amlodipine", "susp_starch_sf", 1.0, None, "refrigerate", None),
    ("enalapril", "susp_sucrose", 1.0, 60, "refrigerate", "Published stability study, 1 mg/mL in 1:1 suspending vehicle"),
    ("spironolactone", "susp_sucrose", 5.0, 30, "refrigerate", "Published stability data (conservative BUD)"),
    ("spironolactone", "susp_sugar_free", 5.0, 30, "refrigerate", "Published stability data (conservative BUD)"),
    ("hydrochlorothiazide", "susp_sucrose", 5.0, 60, "room temperature", "Published stability data"),
    ("sildenafil", "susp_sucrose", 2.5, 90, "room temperature", "Published stability study, 2.5 mg/mL in 1:1 suspending vehicle"),
    ("sildenafil", "susp_sugar_free", 2.5, None, "room temperature", None),
    ("baclofen", "susp_sugar_free", 5.0, 35, "refrigerate", "Published stability data"),
    ("baclofen", "susp_starch_sf", 5.0, None, "refrigerate", None),
    ("gabapentin", "susp_sucrose", 100.0, 90, "refrigerate", "Published stability study, 100 mg/mL in 1:1 suspending vehicle"),
    ("gabapentin", "susp_starch_sf", 100.0, None, "refrigerate", None),
    ("gabapentin", "syrup_aspartame", 50.0, None, "refrigerate", None),
    ("metronidazole", "susp_sucrose", 50.0, 90, "room temperature", "Published stability study, 50 mg/mL in 1:1 suspending vehicle"),
    ("metronidazole", "susp_starch_sf", 50.0, None, "room temperature", None),
    ("ursodiol", "susp_sucrose", 25.0, 60, "room temperature", "Published stability study, 25 mg/mL in 1:1 suspending vehicle"),
    ("levothyroxine", "cap_mcc_hpmc", None, None, "room temperature", None),
    ("levothyroxine", "cap_lactose_gelatin", None, None, "room temperature", None),
    ("levothyroxine", "cap_mcc_gelatin", None, None, "room temperature", None),
    ("ketoprofen", "plo_gel", None, None, "room temperature", None),
    ("ketoprofen", "hydrophilic_ointment", None, None, "room temperature", None),
    ("diclofenac", "plo_gel", None, None, "room temperature", None),
    ("diclofenac", "hydrophilic_ointment", None, None, "room temperature", None),
    ("lidocaine", "hydrophilic_ointment", None, None, "room temperature", None),
    ("lidocaine", "anhydrous_petrolatum", None, None, "room temperature", None),
]

# ---------------------------------------------------------------------------
# Dose rules. population: pediatric (< 18 y) | adult.
# For oral drugs: mg/kg/day range and absolute mg/day ceiling.
# For topicals: max concentration in percent.
# ---------------------------------------------------------------------------
DOSE_RULES = [
    # drug, population, mg/kg/day min, mg/kg/day max, mg/day min, mg/day max, max %
    ("omeprazole", "pediatric", 0.7, 3.3, None, 40, None),
    ("omeprazole", "adult", None, None, 10, 40, None),
    ("lansoprazole", "pediatric", 0.7, 3.0, None, 30, None),
    ("lansoprazole", "adult", None, None, 15, 30, None),
    ("amlodipine", "pediatric", 0.05, 0.6, None, 10, None),
    ("amlodipine", "adult", None, None, 2.5, 10, None),
    ("enalapril", "pediatric", 0.08, 0.6, None, 40, None),
    ("enalapril", "adult", None, None, 2.5, 40, None),
    ("spironolactone", "pediatric", 1.0, 3.3, None, 100, None),
    ("spironolactone", "adult", None, None, 12.5, 200, None),
    ("hydrochlorothiazide", "pediatric", 1.0, 3.0, None, 100, None),
    ("hydrochlorothiazide", "adult", None, None, 12.5, 50, None),
    ("sildenafil", "pediatric", 1.5, 6.0, None, 60, None),
    ("sildenafil", "adult", None, None, 15, 60, None),
    ("baclofen", "pediatric", 0.3, 2.0, None, 60, None),
    ("baclofen", "adult", None, None, 15, 80, None),
    ("gabapentin", "pediatric", 10, 50, None, 3600, None),
    ("gabapentin", "adult", None, None, 300, 3600, None),
    ("metronidazole", "pediatric", 15, 50, None, 2250, None),
    ("metronidazole", "adult", None, None, 500, 4000, None),
    ("ursodiol", "pediatric", 10, 30, None, None, None),
    ("ursodiol", "adult", 8, 15, None, None, None),
    ("levothyroxine", "adult", None, None, 0.0125, 0.3, None),
    ("ketoprofen", "adult", None, None, None, None, 10),
    ("diclofenac", "adult", None, None, None, None, 10),
    ("lidocaine", "adult", None, None, None, None, 5),
    ("lidocaine", "pediatric", None, None, None, None, 4),
]
