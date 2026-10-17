"""Every Cypher query the product depends on, in one place.

The agents only reason through these queries. Most of them walk IS_A paths of
variable length, so one rule written against a class or ingredient group
(e.g. "azo dyes", "NSAIDs", "fructose sources") applies to every member.
"""

# --- Order and patient context ---------------------------------------------

ORDER_CONTEXT = """
MATCH (o:Order {id: $order_id})-[:FILLS]->(rx:Prescription)-[:FOR_PATIENT]->(p:Patient)
MATCH (rx)-[:PRESCRIBES]->(d:Drug)
OPTIONAL MATCH (doc:Prescriber)-[:WROTE]->(rx)
RETURN o, rx, p, d, doc
"""

PATIENT_PROFILE = """
MATCH (p:Patient {id: $patient_id})
OPTIONAL MATCH (p)-[hc:HAS_CONDITION]->(c:Condition)
WITH p, collect(DISTINCT {name: c.name, derived: hc.derived}) AS conditions
OPTIONAL MATCH (p)-[:ALLERGIC_TO]->(a)
WITH p, conditions, collect(DISTINCT a.name) AS allergies
OPTIONAL MATCH (p)-[:AVOIDS]->(v)
WITH p, conditions, allergies, collect(DISTINCT v.name) AS avoids
OPTIONAL MATCH (p)-[:TAKES]->(m:Drug)
WITH p, conditions, allergies, avoids, collect(DISTINCT m.name) AS meds
OPTIONAL MATCH (p)-[:HAD_REACTION]->(r:Excipient)
WITH p, conditions, allergies, avoids, meds, collect(DISTINCT r.name) AS reactions
OPTIONAL MATCH (p)-[:TOLERATED]->(b:Base)
RETURN p, conditions, allergies, avoids, meds, reactions, collect(DISTINCT b.name) AS tolerated
"""

# Agent memory: what happened on this patient's earlier orders.
PATIENT_ORDER_HISTORY = """
MATCH (o:Order)-[:FILLS]->(:Prescription)-[:FOR_PATIENT]->(p:Patient {id: $patient_id})
WHERE o.id <> $order_id
OPTIONAL MATCH (o)-[:FILLS]->(:Prescription)-[:PRESCRIBES]->(d:Drug)
OPTIONAL MATCH (o)-[:PROPOSED]->(f:Formulation)-[:USES_BASE]->(b:Base)
RETURN o.id AS order_id, o.status AS status, d.name AS drug, b.name AS base, o.created_at AS created_at
ORDER BY o.created_at DESC
"""

SET_DERIVED_CONDITIONS = """
MATCH (p:Patient {id: $patient_id})
OPTIONAL MATCH (p)-[old:HAS_CONDITION {derived: true}]->(:Condition)
DELETE old
WITH DISTINCT p
UNWIND $condition_ids AS cid
MATCH (c:Condition {id: cid})
MERGE (p)-[:HAS_CONDITION {derived: true}]->(c)
"""

# --- Formulation ------------------------------------------------------------

# Bases this drug is known to be stable in, for the prescribed route.
CANDIDATE_BASES = """
MATCH (d:Drug {id: $drug_id})-[s:STABLE_IN]->(b:Base)-[:FOR_FORM]->(f:DosageForm {route: $route})
RETURN b.id AS base_id, b.name AS base, f.id AS form_id, f.name AS form, f.liquid AS liquid,
       s.conc_mg_per_ml AS conc_mg_per_ml,
       coalesce(s.bud_days, b.usp_default_bud_days) AS bud_days,
       s.bud_days IS NOT NULL AS has_study, s.storage AS storage, s.reference AS reference
"""

# Dosage forms the patient's conditions call for (e.g. dysphagia -> liquid).
PREFERRED_FORMS = """
MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)-[:PREFERS_FORM]->(f:DosageForm)
RETURN DISTINCT f.id AS form_id, c.name AS because
"""

# Ingredients in a base or product that the patient is allergic to, avoids,
# or reacted to before. Walks the ingredient taxonomy, so an allergy to
# "Azo dye" catches FD&C Red No. 40.
INGREDIENT_ALLERGY_CONFLICTS = """
UNWIND $item_ids AS item_id
MATCH (x {id: item_id})-[:CONTAINS]->(e:Excipient)
MATCH path = (e)-[:IS_A*0..4]->(trigger)
MATCH (p:Patient {id: $patient_id})-[r:ALLERGIC_TO|AVOIDS|HAD_REACTION]->(trigger)
RETURN DISTINCT item_id, e.name AS ingredient, trigger.name AS trigger, type(r) AS relation,
       [n IN nodes(path) | n.name] AS chain
"""

# Ingredients that are a problem for one of the patient's conditions.
INGREDIENT_CONDITION_CONFLICTS = """
UNWIND $item_ids AS item_id
MATCH (x {id: item_id})-[:CONTAINS]->(e:Excipient)
MATCH path = (e)-[:IS_A*0..4]->(g)-[c:CAUTION_IN]->(cond:Condition)<-[:HAS_CONDITION]-(p:Patient {id: $patient_id})
RETURN DISTINCT item_id, e.name AS ingredient, cond.name AS condition, c.severity AS severity, c.note AS note,
       [n IN nodes(path) | n.name] + [cond.name] AS chain
"""

# Ingredients that interact with the prescribed drug or a drug the patient takes.
INGREDIENT_DRUG_INTERACTIONS = """
UNWIND $item_ids AS item_id
MATCH (x {id: item_id})-[:CONTAINS]->(e:Excipient)-[:IS_A*0..4]->(g)-[i:INTERACTS_WITH]-(t)
MATCH (d:Drug)-[:IS_A*0..4]->(t)
WHERE d.id IN $drug_ids
RETURN DISTINCT item_id, e.name AS ingredient, d.name AS drug, i.severity AS severity, i.effect AS effect
"""

# --- Safety -----------------------------------------------------------------

DRUG_ALLERGY = """
MATCH (p:Patient {id: $patient_id})-[:ALLERGIC_TO]->(a)
MATCH path = (d:Drug {id: $drug_id})-[:IS_A*0..4]->(a)
RETURN a.name AS allergy, [n IN nodes(path) | n.name] AS chain
"""

DRUG_CROSS_REACTIVITY = """
MATCH (p:Patient {id: $patient_id})-[:ALLERGIC_TO]->(a)
MATCH (d:Drug {id: $drug_id})-[:IS_A*0..4]->(x)-[cr:CROSS_REACTS_WITH]-(y)
MATCH (a)-[:IS_A*0..4]->(y)
RETURN DISTINCT a.name AS allergy, x.name AS drug_class, y.name AS related_class, cr.severity AS severity, cr.note AS note
"""

DRUG_INTERACTIONS = """
MATCH (d:Drug {id: $drug_id})-[:IS_A*0..4]->(x)
MATCH (p:Patient {id: $patient_id})-[:TAKES]->(m:Drug)-[:IS_A*0..4]->(y)
MATCH (x)-[i:INTERACTS_WITH]-(y)
WHERE m.id <> d.id
RETURN DISTINCT m.name AS other_drug, x.name AS via, y.name AS other_via, i.severity AS severity, i.effect AS effect
"""

DRUG_CONDITION_CAUTIONS = """
MATCH (d:Drug {id: $drug_id})-[:IS_A*0..4]->(x)-[c:CAUTION_IN]->(cond:Condition)<-[:HAS_CONDITION]-(p:Patient {id: $patient_id})
RETURN DISTINCT x.name AS via, cond.name AS condition, c.severity AS severity, c.note AS note
"""

DOSE_RULE = """
MATCH (d:Drug {id: $drug_id})-[:HAS_DOSE_RULE]->(r:DoseRule {population: $population})
RETURN r
"""

# Commercial (FDA-labeled) products of the same drug in acceptable forms.
COMMERCIAL_PRODUCTS = """
MATCH (pr:Product)-[:OF_DRUG]->(d:Drug {id: $drug_id})
MATCH (pr)-[:IN_FORM]->(f:DosageForm)
WHERE f.id IN $form_ids
RETURN pr.id AS product_id, pr.brand AS brand, pr.manufacturer AS manufacturer, f.name AS form, pr.source AS source
"""

# --- Lookups used by the intake agent --------------------------------------

FIND_DRUG = """
MATCH (d:Drug)
WHERE toLower(d.name) = toLower($name) OR toLower($name) IN [a IN d.aliases | toLower(a)]
RETURN d.id AS id, d.name AS name
"""

FIND_PATIENT = """
MATCH (p:Patient) WHERE toLower(p.name) = toLower($name)
RETURN p.id AS id, p.name AS name
"""

FIND_PRESCRIBER = """
MATCH (d:Prescriber)
WHERE toLower(d.name) CONTAINS toLower($name)
RETURN d.id AS id, d.name AS name
"""

# --- Writes: order lifecycle, agent trace, review ---------------------------

SET_STATUS = "MATCH (o:Order {id: $order_id}) SET o.status = $status"

LOG_STEP = """
MATCH (o:Order {id: $order_id})
CREATE (s:AgentStep {id: $id, agent: $agent, action: $action, summary: $summary, at: $at})
CREATE (o)-[:HAS_STEP]->(s)
WITH s
UNWIND $used_ids AS uid
MATCH (n {id: uid})
CREATE (s)-[:USED]->(n)
"""

WRITE_FORMULATION = """
MATCH (o:Order {id: $order_id}) MATCH (d:Drug {id: $drug_id})
MATCH (b:Base {id: $base_id}) MATCH (f:DosageForm {id: $form_id})
OPTIONAL MATCH (o)-[:PROPOSED]->(old:Formulation)
DETACH DELETE old
WITH o, d, b, f
CREATE (x:Formulation) SET x = $props
CREATE (o)-[:PROPOSED]->(x) CREATE (x)-[:OF_DRUG]->(d) CREATE (x)-[:USES_BASE]->(b) CREATE (x)-[:IN_FORM]->(f)
"""

WRITE_FINDING = """
MATCH (o:Order {id: $order_id})
CREATE (fd:Finding {id: $id, severity: $severity, category: $category, message: $message, evidence: $evidence, agent: $agent})
CREATE (o)-[:HAS_FINDING]->(fd)
WITH fd
UNWIND $about_ids AS aid
MATCH (n {id: aid})
CREATE (fd)-[:ABOUT]->(n)
"""

CLEAR_ORDER_RESULTS = """
MATCH (o:Order {id: $order_id})
OPTIONAL MATCH (o)-[:HAS_FINDING]->(fd:Finding)
OPTIONAL MATCH (o)-[:HAS_STEP]->(s:AgentStep)
DETACH DELETE fd, s
"""

ORDER_RESULT = """
MATCH (o:Order {id: $order_id})
OPTIONAL MATCH (o)-[:PROPOSED]->(f:Formulation)
OPTIONAL MATCH (f)-[:USES_BASE]->(b:Base)
OPTIONAL MATCH (f)-[:IN_FORM]->(df:DosageForm)
RETURN o, f, b.name AS base, df.name AS form
"""

ORDER_FINDINGS = """
MATCH (o:Order {id: $order_id})-[:HAS_FINDING]->(fd:Finding)
RETURN fd.severity AS severity, fd.category AS category, fd.message AS message,
       fd.evidence AS evidence, fd.agent AS agent
"""

ORDER_STEPS = """
MATCH (o:Order {id: $order_id})-[:HAS_STEP]->(s:AgentStep)
OPTIONAL MATCH (s)-[:USED]->(n)
RETURN s.agent AS agent, s.action AS action, s.summary AS summary, s.at AS at, collect(n.name) AS used
ORDER BY at
"""

LIST_ORDERS = """
MATCH (o:Order)
OPTIONAL MATCH (o)-[:FILLS]->(rx:Prescription)-[:FOR_PATIENT]->(p:Patient)
OPTIONAL MATCH (rx)-[:PRESCRIBES]->(d:Drug)
OPTIONAL MATCH (o)-[:HAS_FINDING]->(fd:Finding {severity: 'block'})
RETURN o.id AS order_id, o.status AS status, o.source AS source, p.name AS patient, d.name AS drug,
       count(fd) AS blockers, o.created_at AS created_at
ORDER BY created_at DESC
"""

# Approval teaches the graph: the patient tolerated this base.
APPROVE = """
MATCH (o:Order {id: $order_id})-[:FILLS]->(:Prescription)-[:FOR_PATIENT]->(p:Patient)
MATCH (o)-[:PROPOSED]->(:Formulation)-[:USES_BASE]->(b:Base)
SET o.status = 'APPROVED'
MERGE (p)-[:TOLERATED]->(b)
CREATE (o)-[:REVIEWED]->(:Review {id: $id, decision: 'approved', by: $by, note: $note, at: $at})
"""

REJECT = """
MATCH (o:Order {id: $order_id})
SET o.status = 'REJECTED'
CREATE (o)-[:REVIEWED]->(:Review {id: $id, decision: 'rejected', by: $by, note: $note, at: $at})
"""

# A reported reaction is remembered and excluded from future formulations.
REPORT_REACTION = """
MATCH (p:Patient {id: $patient_id}) MATCH (e:Excipient {id: $excipient_id})
MERGE (p)-[r:HAD_REACTION]->(e) SET r.note = $note, r.at = $at
WITH p, e
OPTIONAL MATCH (p)-[t:TOLERATED]->(b:Base)-[:CONTAINS]->(e)
DELETE t
"""
