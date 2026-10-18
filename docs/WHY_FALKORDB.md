# Why FalkorDB fits this problem (draft)

Compounding decisions are questions about how facts connect, not lookups of single records. *Is any ingredient in this base a kind of thing this patient can't take? Does any drug they take belong to a class that interacts with a class this drug belongs to? Which form of this drug does their plan pay for, and is any product in that form safe for them?* Each answer is a path through the data. A graph database stores those paths directly; FalkorDB lets agents walk them fast enough to do it on every order, many times per order.

## 1. Rules live at the right level, and paths apply them

Drugs and classes share one `IS_A` hierarchy, and so do ingredients and their groups. We write a rule once, where it belongs:

- `(PDE5 inhibitor)-[:INTERACTS_WITH]-(Nitrate)` covers every PDE5 inhibitor against every nitrate.
- `(Fructose source)-[:CAUTION_IN {severity:'block'}]->(Hereditary fructose intolerance)` covers sucrose and sorbitol.
- `(Patient)-[:ALLERGIC_TO]->(Azo dye)` catches FD&C Red No. 40 and Yellow No. 5 in any base or commercial product.

One variable-length pattern, `(e)-[:IS_A*0..4]->(trigger)`, applies them. Adding a new dye to the taxonomy protects every dye-allergic patient immediately, with no code change. In SQL this is recursive CTEs over several join tables for every check, and the rule level (drug vs class vs group) has to be known in advance.

## 2. Safety, availability and insurance in one connected model

The coverage question joins five kinds of data: patient → plan → formulary entry → (drug, dosage form) ← commercial product → ingredient → group ← patient allergy. In FalkorDB that is one traversal, and adding a new kind of fact (a therapeutic alternative, a step-therapy rule, a plan's compound policy) is a new edge type, not a schema migration. This is what lets Compounder tell the doctor "the plan denies the solution; the suspension is covered at $15 and contains nothing the patient reacts to".

## 3. Explanations come for free

Every finding returns its path, e.g. `Soy lecithin → Soy-derived ← Daniel`. The UI draws the evidence graph for each order. Pharmacists and regulators need to see *why*, and in a graph the reason is the query result itself.

## 4. One graph for knowledge, agent coordination and memory

- **Coordination:** agents never call each other. Each picks up an `Order` in the status it owns and writes results, `AgentStep` traces and `Finding`s back to the graph (blackboard pattern). Any step can be re-run or resumed.
- **Memory:** approval writes `(Patient)-[:TOLERATED]->(Base)`; a reported reaction writes `(Patient)-[:HAD_REACTION]->(Excipient)`. The next order's queries use them automatically, because memory is just more graph.
- **Traceability:** `AgentStep` nodes link to the exact nodes each agent used.

Keeping these in the same database as the knowledge means no syncing between a vector store, a relational store and an agent state store.

## 5. GraphRAG over regulations and plan rules

Policy excerpts are `PolicyChunk` nodes with a FalkorDB **full-text index**, linked by `MENTIONS` edges to the drugs, forms and plans they talk about. A question is answered from full-text hits **plus** graph expansion to every excerpt and live formulary entry connected to the entities in the question. That finds the relevant rule even when the wording differs, and it grounds the answer in current coverage data rather than stale text.

## 6. Speed for interactive agents

FalkorDB is an in-memory graph database built on sparse matrices (GraphBLAS) and queried with Cypher. One order runs dozens of multi-hop queries (candidate bases, three conflict checks per base, interactions, coverage across products), and the full demo pipeline for seven orders completes in about a second on a laptop. That keeps the agent loop interactive and leaves room to scale to full formularies and product catalogs.

## 7. Cypher is auditable logic

All decision logic sits in readable Cypher queries (`compounder/queries.py`). A pharmacist or reviewer can read the exact rule that excluded a base or flagged an interaction. The LLM is used only for language tasks: parsing free-text orders, briefing the pharmacist, answering policy questions with citations. Clinical decisions stay deterministic and testable.

## If FalkorDB were removed

Nothing works: candidate selection, every safety check, the commercial-product check, coverage ranking, policy retrieval, agent coordination and memory are all graph queries. The graph is the product, not decoration.
