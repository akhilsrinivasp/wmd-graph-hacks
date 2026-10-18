# Compounder

**Graph-powered agents that design patient-specific compounded medicines, check them for safety, find the version the patient's insurance actually pays for, and draft the messages to the doctor and insurer. Built on FalkorDB.**

Built for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb) (WeMakeDevs × FalkorDB).

**Tracks entered:** Agents That Act on Connected Data · Agent Memory and Coordination

**Demo video:** _add link before submitting_ · **Deployment:** runs locally (FalkorDB in Docker + Streamlit); full setup below.

> ⚠️ **Demo only — not for clinical use.** The pharmacology data is simplified, every patient is synthetic, and every formulation must be checked by a licensed pharmacist.

**Sample reports** (full output of the agents for each demo order: formulation, insurance coverage, message to the prescriber, PA request, compounding procedure, safety findings, evidence graph, agent trace). PDFs open directly on GitHub; the HTML files are single self-contained pages.

| Patient | Case | Report |
|---|---|---|
| Maya, 4 y | Amlodipine liquid; plan denies the solution, covers the suspension | [PDF](docs/samples/maya-chen-amlodipine.pdf) · [HTML](docs/samples/maya-chen-amlodipine.html) |
| Daniel, 55 y | Ketoprofen topical; soy allergy rules out PLO; covered diclofenac alternative | [PDF](docs/samples/daniel-okoro-ketoprofen.pdf) · [HTML](docs/samples/daniel-okoro-ketoprofen.html) |
| Ethan, 45 y | Levothyroxine; dye, lactose and gelatin free; PA request | [PDF](docs/samples/ethan-brooks-levothyroxine.pdf) · [HTML](docs/samples/ethan-brooks-levothyroxine.html) |
| Aisha, 7 y | Gabapentin; fructose intolerance rules out sugar vehicles | [PDF](docs/samples/aisha-rahman-gabapentin.pdf) · [HTML](docs/samples/aisha-rahman-gabapentin.html) |
| Robert, 68 y | Sildenafil blocked with his nitrate | [PDF](docs/samples/robert-hale-sildenafil.pdf) · [HTML](docs/samples/robert-hale-sildenafil.html) |
| Sofia, 6 y | Metronidazole overdose blocked (75 mg/kg/day) | [PDF](docs/samples/sofia-alvarez-metronidazole.pdf) · [HTML](docs/samples/sofia-alvarez-metronidazole.html) |
| Leo, 9 mo | Omeprazole suspension; compounding is the cheapest covered option | [PDF](docs/samples/leo-martins-omeprazole.pdf) · [HTML](docs/samples/leo-martins-omeprazole.html) |

📄 **Read more:** [How compounding works today and where we help](docs/RESEARCH.md) · [Why FalkorDB fits this problem](docs/WHY_FALKORDB.md)

## The problem

In the US, **compounding pharmacies** make custom medicines when no FDA-approved product fits the patient. Common cases are a liquid for a child who can't swallow tablets, or a version without a dye, lactose or gelatin the patient can't take. Under section 503A of the FD&C Act, they compound against a prescription for one named patient. Compounded drugs are not FDA-approved, so the pharmacist carries the safety burden.

To fill one order, a pharmacist has to connect a lot of facts:

- the patient's age, weight, conditions, allergies and current medicines
- which bases (vehicles) the drug is stable in, and the beyond-use date
- every inactive ingredient in that base, and whether the patient can take it. A "dye allergy" has to catch FD&C Red No. 40 because it is an *azo dye*; "fructose intolerance" has to catch sucrose *and* sorbitol.
- drug interactions, weight-based dose limits
- whether a commercial product would already do the job, which matters for 503A

- and **insurance**: plans set coverage per drug *and* dosage form. A doctor writes "amlodipine"; the plan denies the oral solution but would have paid for the suspension. The claim bounces, and patient, doctor and pharmacist all lose days. Doctors can't know every brand, form and formulary rule; pharmacists do. Physicians already handle about 39 prior authorizations a week, spending 13 hours on them ([AMA](https://www.ama-assn.org/practice-management/prior-authorization/fixing-prior-auth-nearly-40-prior-authorizations-week-way)).

That is a graph problem, so we modelled it as one.

## What it does

A team of agents takes an order from intake to a pharmacist-ready formulation:

| Agent | What it does in the graph |
|---|---|
| **Intake** | Validates an e-prescription. Free-text orders are parsed by Claude into a structured `Prescription`, and names are resolved against graph nodes. |
| **History** | Loads the patient's context, **writes derived facts back** (e.g. `Young child (< 6 years)`), and recalls memory from earlier orders. |
| **Formulation** | Finds bases the drug is stable in, keeps the dosage forms the patient's conditions call for, excludes bases whose ingredients conflict with the patient (via multi-hop `IS_A` paths), ranks the rest, then computes the strength, dose volume, quantity, beyond-use date and label directions. |
| **Safety** | Independently checks drug allergy and cross-reactivity, drug–drug and drug–condition interactions, the weight-based dose, the chosen base again, and whether a suitable commercial product exists (from **957 real FDA labels via openFDA**). |
| **Coverage** | Walks patient → plan → formulary entry (drug + dosage form) ← commercial products → ingredients ← patient allergies. Ranks the safe options by prior auth and copay, suggests covered therapeutic alternatives, and drafts a **ready-to-send message to the prescriber** and a **prior-authorization request** that lists why each covered product is unsuitable. |
| **Pharmacist** (human) | Reviews the formulation, findings, evidence graph and agent trace, then approves or rejects. Blocking findings need a documented override. |

**Coordination:** agents never call each other. Each agent picks up an `Order` in the status it owns, writes its results and an `AgentStep` trace (linked to the nodes it used), and moves the order on: `RECEIVED → INTAKE_DONE → CONTEXT_READY → FORMULATED → SAFETY_CHECKED → AWAITING_REVIEW`. The graph is the shared blackboard, so any step can be re-run or resumed.

**Memory:** approving an order adds `(Patient)-[:TOLERATED]->(Base)`. Reporting a reaction adds `(Patient)-[:HAD_REACTION]->(Excipient)` and removes that tolerance. On the next order, the Formulation agent prefers tolerated bases and treats past reactions like allergies. A test covers this: after a reported methylparaben rash, the patient's next order moves to a paraben-free base.

**Compounding procedure:** each formulation comes with a master-formulation-record-style procedure: ingredients with computed amounts (e.g. "10 × amlodipine 5 mg tablets"), equipment, numbered steps, quality checks and label text.

**Structured patient intake:** patient data enters as a validated record (allergies with reaction and severity, history, medications, dietary restrictions, insurance, the doctor's prescription), via a form or JSON import (`data/sample_patient.json`). Every name is matched to a graph node, and details are stored on the relationships.

**Ask the rules (GraphRAG):** regulation and plan-rule excerpts are `PolicyChunk` nodes with a FalkorDB full-text index, linked to the drugs, forms and plans they mention. A plain-English question is answered from full-text hits plus graph expansion to linked excerpts and live formulary facts; the LLM (Claude or Gemini) writes the answer with citations.

**Traceability:** every finding stores its evidence path (e.g. `Soy lecithin → Soy-derived`), and the UI draws the evidence graph for each order.

### Demo cases (all synthetic, insurance plans included)

Coverage results: **Maya** (Acme PPO): the oral solution is denied, Katerzia suspension is covered at $15 with no PA, and a message asks the doctor to specify the suspension. **Daniel** (Part D): ketoprofen compound needs PA at $47, so the agent suggests covered diclofenac 1% gel at $9. **Ethan** (Acme PPO): every covered tablet contains dyes, so a compound PA request is drafted citing them. **Leo** (Medicaid): compounding is the cheapest covered option ($1, no PA).

| Patient | Order | What the graph catches |
|---|---|---|
| Maya, 4 y, azo-dye allergy | Amlodipine 1.5 mg daily | Needs a liquid (derived "young child"). Makes 1 mg/mL suspension, 1.5 mL per dose. Flags that Katerzia/Norliqva are dye-free commercial liquids (503A justification needed). |
| Leo, 9 months | Omeprazole 8 mg daily | 2 mg/mL in 8.4% sodium bicarbonate, 4 mL per dose, 30-day BUD. |
| Aisha, 7 y, hereditary fructose intolerance | Gabapentin 200 mg TID | Excludes sucrose **and** sorbitol vehicles via `fructose source` → picks the starch-based base. |
| Robert, 68 y, on isosorbide mononitrate | Sildenafil 20 mg TID | **Blocks**: PDE5 inhibitor + nitrate (class-level rule). |
| Daniel, 55 y, soy allergy, on warfarin | Ketoprofen 10% topical | Excludes PLO gel (soy lecithin). Warns NSAID + warfarin and renal impairment. No commercial topical ketoprofen exists, so compounding is justified. |
| Sofia, 6 y, 20 kg | Metronidazole 500 mg TID | **Blocks**: 75 mg/kg/day is above the 50 mg/kg/day pediatric maximum. |
| Ethan, 45 y, dye allergy, vegetarian | Levothyroxine 100 mcg | Excludes gelatin capsules (`AVOIDS Animal-derived`) → hypromellose capsule. Finds dye-free commercial levothyroxine solutions. |

## Graph data model

```mermaid
graph LR
  Drug -- IS_A --> DrugClass
  DrugClass -- IS_A --> DrugClass
  Excipient -- IS_A --> ExcipientGroup
  ExcipientGroup -- IS_A --> ExcipientGroup
  Drug -- STABLE_IN --> Base
  Base -- CONTAINS --> Excipient
  Base -- FOR_FORM --> DosageForm
  Drug -- HAS_DOSE_RULE --> DoseRule
  DrugClass -- INTERACTS_WITH --> DrugClass
  ExcipientGroup -- INTERACTS_WITH --> Drug
  DrugClass -- CAUTION_IN --> Condition
  ExcipientGroup -- CAUTION_IN --> Condition
  DrugClass -- CROSS_REACTS_WITH --> DrugClass
  Condition -- PREFERS_FORM --> DosageForm
  Product -- OF_DRUG --> Drug
  Product -- CONTAINS --> Excipient
  Product -- IN_FORM --> DosageForm
  Patient -- HAS_CONDITION --> Condition
  Patient -- ALLERGIC_TO --> ExcipientGroup
  Patient -- AVOIDS --> ExcipientGroup
  Patient -- TAKES --> Drug
  Patient -- TOLERATED --> Base
  Patient -- HAD_REACTION --> Excipient
  Prescriber -- WROTE --> Prescription
  Prescription -- FOR_PATIENT --> Patient
  Prescription -- PRESCRIBES --> Drug
  Order -- FILLS --> Prescription
  Order -- PROPOSED --> Formulation
  Formulation -- USES_BASE --> Base
  Order -- HAS_FINDING --> Finding
  Order -- HAS_STEP --> AgentStep
  AgentStep -- USED --> Patient
  Order -- REVIEWED --> Review
  Patient -- INSURED_BY --> InsurancePlan
  InsurancePlan -- LISTS --> FormularyEntry
  FormularyEntry -- FOR_DRUG --> Drug
  FormularyEntry -- IN_FORM --> DosageForm
  Drug -- ALTERNATIVE_TO --> Drug
  Order -- COVERAGE --> CoverageDecision
  CoverageDecision -- UNDER_PLAN --> InsurancePlan
  PolicyChunk -- MENTIONS --> InsurancePlan
```

Notes:
- Drugs and classes share one `IS_A` hierarchy, and so do excipients and their groups. Rules are written once at the right level, e.g. `(PDE5 inhibitor)-[:INTERACTS_WITH]-(Nitrate)` or `(Fructose source)-[:CAUTION_IN {severity:'block'}]->(Hereditary fructose intolerance)`. Variable-length paths apply them to every member.
- `ALLERGIC_TO` / `CAUTION_IN` / `INTERACTS_WITH` endpoints can be any level of either hierarchy (a drug, a class, an ingredient or an ingredient group).
- `STABLE_IN` carries the concentration, beyond-use date, storage and reference. Without a study, the base's USP <795> default BUD applies.

| Layer | Nodes | Source |
|---|---|---|
| Pharmacology knowledge | 24 drugs, 22 classes, 44 excipients, 17 excipient groups, 12 bases, 7 dosage forms, 27 dose rules, 25 conditions | Curated in `compounder/seed/knowledge.py` (simplified from public references and published compounding stability studies) |
| Commercial products | 957 FDA drug labels with detected inactive ingredients (route-checked against the dosage form) | [openFDA drug label API](https://open.fda.gov/apis/drug/label/), cached in `data/openfda_products.json` |
| Insurance plans and formularies | 3 plans, 21 formulary entries (drug + form), compound policies, therapeutic alternatives | **Synthetic**, modelled on common real formulary patterns (`compounder/seed/insurance.py`) |
| Regulation and plan-rule excerpts | 12 policy chunks with source links, full-text indexed | Paraphrased from FDA (503A/503B), USP <795>, CMS Part D manual; plan rules synthetic (`compounder/seed/policies.py`) |
| Patients, prescribers, prescriptions | 7 / 3 / 7 | Synthetic (`compounder/seed/demo_patients.py`) |
| Orders, formulations, findings, agent steps, reviews | created at runtime | Written by the agents |

## The Cypher the product depends on

All queries live in [`compounder/queries.py`](compounder/queries.py); agents reason only through them. The core ones:

**Which ingredients in these bases is the patient allergic to, avoiding, or previously reacted to?** One allergy to "Azo dye" catches every azo dye in every base.
```cypher
UNWIND $item_ids AS item_id
MATCH (x {id: item_id})-[:CONTAINS]->(e:Excipient)
MATCH path = (e)-[:IS_A*0..4]->(trigger)
MATCH (p:Patient {id: $patient_id})-[r:ALLERGIC_TO|AVOIDS|HAD_REACTION]->(trigger)
RETURN DISTINCT item_id, e.name AS ingredient, trigger.name AS trigger, type(r) AS relation,
       [n IN nodes(path) | n.name] AS chain
```

**Which ingredients are a problem for one of the patient's conditions?**
```cypher
UNWIND $item_ids AS item_id
MATCH (x {id: item_id})-[:CONTAINS]->(e:Excipient)
MATCH path = (e)-[:IS_A*0..4]->(g)-[c:CAUTION_IN]->(cond:Condition)<-[:HAS_CONDITION]-(p:Patient {id: $patient_id})
RETURN DISTINCT item_id, e.name AS ingredient, cond.name AS condition, c.severity AS severity, c.note AS note
```

**Drug–drug interactions at any level of the class hierarchy**
```cypher
MATCH (d:Drug {id: $drug_id})-[:IS_A*0..4]->(x)
MATCH (p:Patient {id: $patient_id})-[:TAKES]->(m:Drug)-[:IS_A*0..4]->(y)
MATCH (x)-[i:INTERACTS_WITH]-(y)
WHERE m.id <> d.id
RETURN DISTINCT m.name AS other_drug, x.name AS via, y.name AS other_via, i.severity AS severity, i.effect AS effect
```

**Candidate bases and beyond-use dates**
```cypher
MATCH (d:Drug {id: $drug_id})-[s:STABLE_IN]->(b:Base)-[:FOR_FORM]->(f:DosageForm {route: $route})
RETURN b.id AS base_id, b.name AS base, f.id AS form_id, f.name AS form, f.liquid AS liquid,
       s.conc_mg_per_ml AS conc_mg_per_ml, coalesce(s.bud_days, b.usp_default_bud_days) AS bud_days,
       s.bud_days IS NOT NULL AS has_study, s.storage AS storage, s.reference AS reference
```

**Insurance: what does the patient's plan pay for, per drug and dosage form?**
```cypher
MATCH (:Patient {id: $patient_id})-[:INSURED_BY]->(pl:InsurancePlan)-[:LISTS]->(fe:FormularyEntry)-[:FOR_DRUG]->(d:Drug)
WHERE d.id IN $drug_ids
MATCH (fe)-[:IN_FORM]->(f:DosageForm)
WHERE f.id IN $form_ids
RETURN d.id AS drug_id, d.name AS drug, f.id AS form_id, f.name AS form, fe.status AS status,
       fe.tier AS tier, fe.copay_usd AS copay, fe.prior_auth AS prior_auth, fe.note AS note
```
The Coverage agent joins this with the commercial products in each form and runs the ingredient-conflict query on them, so a "covered" form only counts if a product in it is safe for this patient.

**Policy GraphRAG: full-text search, then expand through the graph**
```cypher
CALL db.idx.fulltext.queryNodes('PolicyChunk', $q) YIELD node, score
RETURN node.id AS id, node.source AS source, node.text AS text, score ORDER BY score DESC LIMIT $k
```
```cypher
MATCH (c:PolicyChunk)-[:MENTIONS]->(n) WHERE n.id IN $ids
RETURN DISTINCT c.id AS id, c.source AS source, c.url AS url, c.text AS text
```

**Memory: approval teaches the graph**
```cypher
MATCH (o:Order {id: $order_id})-[:FILLS]->(:Prescription)-[:FOR_PATIENT]->(p:Patient)
MATCH (o)-[:PROPOSED]->(:Formulation)-[:USES_BASE]->(b:Base)
SET o.status = 'APPROVED'
MERGE (p)-[:TOLERATED]->(b)
CREATE (o)-[:REVIEWED]->(:Review {id: $id, decision: 'approved', by: $by, note: $note, at: $at})
```

Remove FalkorDB and nothing works: candidate selection, every safety check, the commercial-product check, coverage ranking, policy retrieval, agent coordination and memory are all graph queries. More in [docs/WHY_FALKORDB.md](docs/WHY_FALKORDB.md).

## Setup

### Option A: Docker Compose (everything)

```bash
docker compose up --build
```
Open http://localhost:8501 for the app and http://localhost:3000 for the FalkorDB browser. The demo data is loaded and processed on start.

### Option B: local Python

```bash
docker run -d -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
pip install -r requirements.txt
python cli.py seed      # load knowledge base, openFDA products, demo patients and orders
python cli.py run       # run every pending order through the agents (prints results)
python cli.py export    # HTML + PDF report per order in docs/samples/ (PDF needs: pip install playwright)
streamlit run app.py    # pharmacist UI
pytest                  # end-to-end tests (needs FalkorDB running)
```

**Optional LLM:** set `ANTHROPIC_API_KEY` (Claude Opus 5.5 by default, override with `COMPOUNDER_MODEL`) **or** `GEMINI_API_KEY` (Gemini, free tier available from Google AI Studio; default `gemini-flash-latest`, override with `GEMINI_MODEL`) to enable free-text order parsing, the pharmacist brief and written policy answers. If both are set, Claude is used unless `COMPOUNDER_LLM=gemini`. Everything else works without a key.

**FalkorDB Cloud:** set `FALKORDB_URL=redis://USER:PASSWORD@HOST:PORT` (see `.env.example`).

**Refresh product data from openFDA:** `python -m compounder.seed.openfda`

## Project layout

```
compounder/
  queries.py           every Cypher query
  agents/              intake, history, formulation, safety, orchestrator
  seed/knowledge.py    curated pharmacology knowledge base
  seed/openfda.py      openFDA label importer (inactive ingredients)
  seed/demo_patients.py synthetic patients and prescriptions
  seed/loader.py       writes everything into FalkorDB
  agents/coverage.py   insurance coverage, prescriber message, PA request
  procedure.py         step-by-step compounding procedure
  intake_schema.py     structured patient record (Pydantic) + import
  policy.py            GraphRAG over policy excerpts
  seed/insurance.py    synthetic plans and formularies
  seed/policies.py     regulation / plan-rule excerpts
  llm.py               LLM (Claude or Gemini): free-text parsing, pharmacist brief, policy answers
  viz.py               evidence graph (Graphviz)
app.py                 Streamlit pharmacist UI
cli.py                 command-line demo
tests/                 end-to-end tests against FalkorDB
```

## Design decisions

- **The model does not make clinical decisions.** Base choice, dose checks and interactions are deterministic graph queries, so every decision can be traced and tested. An LLM (Claude or Gemini) is used where language is the problem: reading messy free-text orders, summarising findings for the pharmacist and answering policy questions.
- **Human in the loop.** Agents propose; a pharmacist approves. That matches how 503A compounding works.
- **Rules at the right level of abstraction.** One `CAUTION_IN` edge from `Fructose source` covers sucrose and sorbitol. Adding a new dye to the taxonomy instantly protects every dye-allergic patient.
- **Real regulatory context.** The commercial-product check uses real FDA label data. 503A pharmacies shouldn't compound copies of commercially available drugs without a documented clinical reason.

## Limitations

- The knowledge base is small and simplified. Dose ranges and stability data are illustrative and not verified for clinical use.
- openFDA inactive-ingredient lists often cover all strengths of a product together, so the commercial check is conservative.
- Insurance plans are synthetic. Production use needs real formulary feeds (e.g. CMS Part D formulary files, PBM data) and real PA submission (e.g. ePA).
- Compounding procedures are templates per dosage form, not validated master formulation records.
- No renal dose adjustment by creatinine clearance, no drug-strength matching for commercial products, and no compounding worksheets yet.

## Hackathon rules checklist

| Requirement (official rules) | Where |
|---|---|
| FalkorDB is the primary database and does real work | Every agent decision is a Cypher query: [`compounder/queries.py`](compounder/queries.py), [Why FalkorDB](docs/WHY_FALKORDB.md) |
| Public source-code repository | This repo |
| README with setup instructions and graph data model | [Setup](#setup), [Graph data model](#graph-data-model) |
| Cypher queries the product depends on | [The Cypher the product depends on](#the-cypher-the-product-depends-on), [`compounder/queries.py`](compounder/queries.py) |
| Demo video | Link at the top of this README |
| Live deployment or complete local setup | Local setup: [Setup](#setup) |
| Tracks entered | Agents That Act on Connected Data; Agent Memory and Coordination |
| Allowed data only | openFDA labels and FDA/CMS/USP documents (public); patients, prescribers and insurance plans are synthetic |
| Work done during the hackathon | All commits are dated from Oct 17, 2026 (event: Oct 15–18) |
| AI coding assistants disclosed | Below |

## AI assistance disclosure

Per the hackathon rules, we disclose that we used **Claude Code** as an AI coding assistant.

The team chose the problem (compounding pharmacies), defined the scope, and drove the product direction across iterations: structured patient intake, step-by-step compounding procedures, the insurance angle (plans covering one dosage form but denying another, and bridging doctor, pharmacist and insurer), shareable reports, and the rules review. Claude Code was used for research on US compounding regulations and to implement the code and tests under the team's direction. The team reviewed and tested the output and can explain the graph model, the queries and the design decisions. The app also optionally calls an LLM API (Claude or Gemini) at runtime for language tasks, as described above.

## License

MIT
