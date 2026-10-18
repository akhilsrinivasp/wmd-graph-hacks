"""GraphRAG over policy text: full-text search in FalkorDB, expanded through
the graph to live formulary facts, then (optionally) answered by Claude."""
from compounder import db, llm
from compounder.seed.policies import POLICY_CHUNKS

STOP = {"the", "a", "an", "is", "are", "for", "of", "to", "in", "and", "or", "does", "do", "can", "my", "what",
        "which", "how", "why", "if", "on", "be", "it", "with", "this", "that", "will", "would", "covered", "cover"}


def load():
    db.run("MATCH (c:PolicyChunk) DETACH DELETE c")
    db.run("MERGE (:Concept {id: 'compound', name: 'Compounding'})")
    db.run("""UNWIND $rows AS r CREATE (c:PolicyChunk {id: r.id, source: r.source, url: r.url, text: r.text})
              WITH c, r UNWIND r.mentions AS m MATCH (n {id: m}) CREATE (c)-[:MENTIONS]->(n)""",
           {"rows": POLICY_CHUNKS})
    try:
        db.run("CALL db.idx.fulltext.createNodeIndex('PolicyChunk', 'text', 'source')")
    except Exception:
        pass  # index already exists


def retrieve(question: str, k: int = 5) -> dict:
    words = [w.strip("?.,!'\"").lower() for w in question.split()]
    terms = [w for w in words if len(w) > 2 and w not in STOP]
    query = " | ".join(terms) or question
    hits = db.run("""CALL db.idx.fulltext.queryNodes('PolicyChunk', $q) YIELD node, score
                     RETURN node.id AS id, node.source AS source, node.url AS url, node.text AS text, score
                     ORDER BY score DESC LIMIT $k""", {"q": query, "k": k})
    # Entities named in the question (drugs, plans, forms) -> live formulary facts from the graph
    ents = db.run("""MATCH (n) WHERE (n:Drug OR n:InsurancePlan OR n:DosageForm)
                     AND any(t IN $terms WHERE toLower(n.name) CONTAINS t OR n.id CONTAINS t)
                     RETURN n.id AS id, labels(n)[0] AS label""", {"terms": terms})
    ids = [e["id"] for e in ents]
    plans = [e["id"] for e in ents if e["label"] == "InsurancePlan"]
    drugs = [e["id"] for e in ents if e["label"] == "Drug"]
    facts = db.run("""MATCH (pl:InsurancePlan)-[:LISTS]->(fe:FormularyEntry)-[:FOR_DRUG]->(d:Drug), (fe)-[:IN_FORM]->(f)
                      WHERE (size($plans) = 0 OR pl.id IN $plans) AND (size($drugs) = 0 OR d.id IN $drugs)
                      RETURN pl.name AS plan, d.name AS drug, f.name AS form, fe.status AS status,
                             fe.copay_usd AS copay, fe.prior_auth AS pa, fe.note AS note""",
                   {"plans": plans, "drugs": drugs}) if (plans or drugs) else []
    # Policies linked through the graph to those entities, even without matching words
    linked = db.run("""MATCH (c:PolicyChunk)-[:MENTIONS]->(n) WHERE n.id IN $ids
                       RETURN DISTINCT c.id AS id, c.source AS source, c.url AS url, c.text AS text""",
                    {"ids": ids}) if ids else []
    seen, chunks = set(), []
    for c in hits + linked:
        if c["id"] not in seen:
            seen.add(c["id"])
            chunks.append(c)
    return {"chunks": chunks[:8], "facts": facts}


def answer(question: str) -> dict:
    ctx = retrieve(question)
    out = {**ctx, "answer": None}
    if llm.available() and (ctx["chunks"] or ctx["facts"]):
        out["answer"] = llm.answer_policy(question, ctx)
    return out
