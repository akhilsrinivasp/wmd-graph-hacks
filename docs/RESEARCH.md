# How compounding works today, and where Compounder helps

## 1. The process today (US, 503A pharmacy)

A compounding pharmacy makes a medicine for one named patient when no FDA-approved product fits: a liquid for a child who can't swallow tablets, a version without a dye or lactose the patient reacts to, a strength that isn't sold. Under section 503A of the FD&C Act this requires a valid prescription for that patient, and compounded drugs are not FDA-approved, so FDA does not check their safety, effectiveness or quality before use ([FDA Q&A](https://www.fda.gov/drugs/human-drug-compounding/compounding-and-fda-questions-and-answers), [FDA laws and policies](https://www.fda.gov/drugs/human-drug-compounding/compounding-laws-and-policies)). The pharmacist carries the safety burden.

A typical order goes like this:

1. **Prescription arrives.** It is often just a drug and dose ("amlodipine 1.5 mg daily"), sometimes free text, fax or phone. The form is often missing, and so is any note on allergies to inactive ingredients.
2. **Pharmacist gathers context.** Allergies, conditions, current medicines and weight come from the profile, the patient or calls to the clinic.
3. **Checks whether a commercial product works.** 503A pharmacies should not regularly compound essentially copies of commercially available products, so the pharmacist checks what is sold and whether its inactive ingredients suit this patient. Ingredient lists sit inside each product label, strength by strength.
4. **Designs the formulation.** Picks a base the drug is known to be stable in, a concentration, and a beyond-use date from a stability study, or the USP <795> default when there is no study. Checks every base ingredient against allergies and conditions (sugar for diabetes, sorbitol and sucrose for fructose intolerance, aspartame for PKU, benzyl alcohol for neonates).
5. **Safety checks.** Drug allergy and cross-reactivity, interactions with current medicines, weight-based dose range.
6. **Insurance.** Checks the plan's formulary, which is often set per drug *and dosage form*. Compounds frequently need prior authorization (PA), and Medicare Part D pays only for the ingredients that are themselves Part D drugs.
7. **Back-and-forth with the prescriber** when the dose is wrong, the form isn't covered, or a covered alternative exists.
8. **Compounds and documents** a master formulation record and compounding record, labels with the beyond-use date, and has a second pharmacist verify.

## 2. Pain points

**Patient**
- Waits days for a medicine because a claim is denied for a technicality (the plan covers the suspension but not the solution, or the capsule but not the tablet).
- Pays cash or abandons treatment when coverage isn't sorted out.
- Is exposed to the ingredient they react to when nobody checks inactive ingredients across every product.

**Doctor**
- Doesn't know every brand, dosage form, inactive ingredient or formulary rule. They write "amlodipine", the plan denies the form the pharmacy chose, and the office then has to rewrite the prescription or file a PA.
- Prior authorization load is heavy. In an AMA survey of 1,000 physicians (late 2024), practices completed **39 PA requests per physician per week**, physicians and staff spent **13 hours a week** on them, and **40%** of physicians have staff who work only on PAs. **89%** said PA increases burnout, and more than a quarter reported that PA led to a serious adverse event for a patient ([AMA](https://www.ama-assn.org/practice-management/prior-authorization/fixing-prior-auth-nearly-40-prior-authorizations-week-way)).

**Pharmacist**
- Holds the knowledge that bridges doctor and insurer (which form is covered, which product is dye-free, what the PA needs) but spends time on phone calls and faxes to pass it on.
- Formulation design means cross-referencing stability literature, base compositions, label ingredient lists and patient records by hand.
- Regulations (503A conditions, USP <795>, Part D compound rules) and plan rules are spread across long documents.

**Insurer**
- Receives incomplete PA requests and then appeals. In 2023, Medicare Advantage insurers received more than 50 million PA requests; 11.7% of denials were appealed, and **81.7% of appealed denials were fully or partly overturned** (KFF analysis of CMS data, cited by the [AMA](https://www.ama-assn.org/practice-management/prior-authorization/fixing-prior-auth-nearly-40-prior-authorizations-week-way)). Most of that work was avoidable.

**Time.** We could not find a published figure for how long a pharmacist spends designing and clearing one compounded prescription. From the steps above, a non-trivial order (several lookups, a prescriber call, a PA) plausibly takes from tens of minutes to days of elapsed time. This is an estimate to validate with pharmacists, not a measured number.

## 3. What Compounder changes

| Step | Today | With Compounder |
|---|---|---|
| Patient context | Scattered profile, calls | Structured record in the graph (allergies with reaction and severity, history, meds, insurance, prescription), validated on entry |
| Commercial product check | Read labels one by one | 957 FDA labels in the graph, inactive ingredients checked against the patient in one query |
| Formulation design | Literature + base sheets + manual cross-check | Agents pick base, strength, beyond-use date and quantity; excluded bases show the exact ingredient path that ruled them out |
| Procedure | Written by hand | Step-by-step procedure with computed quantities, quality checks and label text |
| Safety | Separate tools | Allergy, cross-reactivity, interactions, dose per kg, ingredient checks; every finding carries evidence |
| Insurance | Formulary lookup, trial-and-error claims | Coverage agent ranks safe options by prior auth and copay per drug *and* form, suggests covered alternatives |
| Prescriber / insurer communication | Calls, faxes, rewritten prescriptions | Ready-to-send prescriber message ("please specify the oral suspension; covered at $15, no PA") and a PA request listing why each covered product is unsuitable |
| Rules lookup | Read long documents | Ask in plain English; answers cite the policy excerpts and live formulary facts |
| Memory | Pharmacist's memory | Tolerated bases and reported reactions are stored and used on the next order |

Value: fewer denied claims and PA round trips (time for doctor, pharmacist and insurer), lower copays for patients by steering to the covered form, and safer formulations because every ingredient is checked.

## 4. Caveats

- Insurance plans in the demo are synthetic, modelled on common real formulary patterns. Production use needs real formulary feeds (e.g. CMS Part D formulary files, PBM data).
- Pharmacology data is simplified and not for clinical use. A licensed pharmacist approves every order.
