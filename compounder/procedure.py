"""Compounding procedure generator (Master Formulation Record style, USP <795>).

Turns the chosen formulation into step-by-step instructions with computed
quantities. DEMO ONLY: a pharmacist must verify every step before use.
"""
import math

# Commercial source used as the active ingredient when making liquids
# (tablets/capsules are crushed or opened). Others are weighed as USP powder.
SOURCE_UNITS = {
    "omeprazole": ("delayed-release capsule", 20), "lansoprazole": ("delayed-release capsule", 30),
    "amlodipine": ("tablet", 5), "enalapril": ("tablet", 10), "spironolactone": ("tablet", 25),
    "hydrochlorothiazide": ("tablet", 25), "sildenafil": ("tablet", 20), "baclofen": ("tablet", 10),
    "gabapentin": ("capsule", 300), "metronidazole": ("tablet", 250), "ursodiol": ("capsule", 300),
}
CAPSULE_FILL_MG = 200  # approximate fill weight of a size 3 capsule with microcrystalline cellulose


def _g(x: float) -> str:
    return f"{x:.3g} g" if x >= 1 else f"{x * 1000:.3g} mg"


def build(drug_id: str, drug_name: str, base: dict, plan: dict, rx: dict) -> dict:
    form = base["form_id"]
    storage = base.get("storage") or "room temperature"
    label = [plan["directions"], f"Discard {base['bud_days']} days after the compounding date (beyond-use date).",
             "Compounded medication. Keep out of reach of children."]

    if base["liquid"]:
        conc, vol = base["conc_mg_per_ml"], plan["quantity"]
        total_mg = conc * vol
        unit, strength = SOURCE_UNITS.get(drug_id, ("USP powder", None))
        if strength:
            n = math.ceil(total_mg / strength)
            source = f"{n} × {drug_name} {strength:g} mg {unit}s ({n * strength:g} mg; {total_mg:g} mg needed)"
            first = (f"Open the capsules and empty the pellets into the mortar." if "capsule" in unit
                     else "Place the tablets in the mortar and crush to a fine, uniform powder.")
        else:
            source = f"{drug_name} USP powder {total_mg:g} mg"
            first = "Weigh the powder and place it in the mortar."
        steps = [
            f"Calculate: {conc:g} mg/mL × {vol:g} mL = {total_mg:g} mg {drug_name}.",
            f"Gather {source}.",
            first,
            f"Add a small amount of {base['base']} and levigate into a smooth, lump-free paste.",
            "Add more vehicle in portions (geometric dilution), mixing well after each addition.",
            f"Transfer to a calibrated amber bottle, rinse the mortar with vehicle, add the rinse, then "
            f"add vehicle to a final volume of {vol:g} mL (q.s.).",
            "Cap and shake well for 1 minute.",
            f"Label and store: {storage}.",
        ]
        equipment = ["Mortar and pestle", "Graduated cylinder", "Amber plastic bottle", "Oral syringes"]
        qc = ["Uniform appearance, no clumps", "Final volume checked", "Re-disperses easily on shaking",
              "Second person verifies calculation"]
        ingredients = [source, f"{base['base']} q.s. to {vol:g} mL"]
    elif form == "capsule":
        n = plan["quantity"] + 2  # make two extra to allow for loss
        dose_mg = rx["dose_mg"]
        api_mg = dose_mg * n
        blend_mg = CAPSULE_FILL_MG * n
        steps = [f"Calculate for {n} capsules ({plan['quantity']} + 2 extra): {dose_mg:g} mg × {n} = {api_mg:g} mg {drug_name}."]
        if dose_mg < 1:
            steps.append(f"Dose is under 1 mg per capsule, so weigh an aliquot: mix 100 mg {drug_name} USP with "
                         f"9.9 g filler (1:100 trituration), then use {api_mg * 100 / 1000:.3g} g of this mix.")
        else:
            steps.append(f"Weigh {_g(api_mg / 1000)} {drug_name} USP powder.")
        steps += [
            f"Weigh filler (from {base['base']}) to a total blend of {_g(blend_mg / 1000)}.",
            "Mix drug and filler by geometric dilution until uniform.",
            f"Fill {n} capsules (size 3) using the capsule machine or punch method; target {CAPSULE_FILL_MG} mg each.",
            "Weigh 10 capsules; each must be within ±10% of target weight.",
            f"Package {plan['quantity']} capsules, label and store: {storage}.",
        ]
        equipment = ["Analytical balance", "Mortar and pestle", "Capsule filling machine", "Capsule shells (size 3)"]
        qc = ["Capsule weight within ±10%", "Content uniformity (visual)", "Second person verifies calculation"]
        ingredients = [f"{drug_name} USP {api_mg:g} mg", f"{base['base']} to {blend_mg:g} mg total blend"]
    else:
        grams = plan["quantity"]
        pct = rx.get("concentration_pct") or 0
        api_g = grams * pct / 100
        steps = [
            f"Calculate: {pct:g}% × {grams:g} g = {api_g:.3g} g {drug_name}.",
            f"Weigh {api_g:.3g} g {drug_name} USP powder and {grams - api_g:.3g} g {base['base']}.",
            "Levigate the drug powder with a few drops of a compatible levigating agent until smooth.",
            "Incorporate the base in portions (geometric dilution) on an ointment slab until uniform.",
            "Pass through an ointment mill (or mix in an electronic mortar) for a smooth, grit-free product.",
            f"Fill into a {grams:g} g jar or tube, label and store: {storage}.",
        ]
        equipment = ["Analytical balance", "Ointment slab and spatulas", "Ointment mill / electronic mortar", "Jar or tube"]
        qc = ["Smooth, no grit or particles", "Final weight checked", "Second person verifies calculation"]
        ingredients = [f"{drug_name} USP {api_g:.3g} g", f"{base['base']} {grams - api_g:.3g} g"]

    return {"procedure": steps, "ingredients": ingredients, "equipment": equipment, "qc": qc, "label": label}
