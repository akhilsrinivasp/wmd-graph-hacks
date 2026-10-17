"""Streamlit UI for pharmacists.  Run:  streamlit run app.py"""
import time
import uuid

import streamlit as st

from compounder import db, llm
from compounder import queries as Q
from compounder.agents.base import props
from compounder.agents.orchestrator import process, process_pending
from compounder.report import order_report
from compounder.seed import demo_patients
from compounder.seed.loader import add_patient, add_prescription, create_order, load_all
from compounder.viz import COLORS, order_dot

st.set_page_config(page_title="Compounder", page_icon="💊", layout="wide")

SEVERITY_BOX = {"block": st.error, "warn": st.warning, "info": st.info}
STATUS_LABEL = {
    "RECEIVED": "Received", "INTAKE_DONE": "Intake done", "CONTEXT_READY": "Context ready",
    "FORMULATED": "Formulated", "AWAITING_REVIEW": "Awaiting pharmacist", "APPROVED": "Approved",
    "REJECTED": "Rejected", "NEEDS_ATTENTION": "Needs attention",
}


def db_ok() -> bool:
    try:
        db.run("RETURN 1")
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("💊 Compounder")
    st.caption("Graph-powered agents for compounding pharmacies, on FalkorDB.")
    if not db_ok():
        st.error("Can't reach FalkorDB. Start it with `docker compose up -d`.")
        st.stop()
    n_nodes = db.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
    st.success(f"FalkorDB connected · {n_nodes:,} nodes")
    if n_nodes == 0:
        st.info("The graph is empty. Load the demo data to start.")
    if st.button("Reset and load demo data", use_container_width=True):
        with st.spinner("Loading knowledge base, openFDA products and demo patients..."):
            load_all()
        st.rerun()
    if st.button("Run agents on pending orders", type="primary", use_container_width=True):
        with st.spinner("Agents working..."):
            done = process_pending()
        st.toast(f"Processed {len(done)} order(s)")
        st.rerun()
    st.divider()
    st.caption("Claude: " + ("connected" if llm.available() else "not configured (set ANTHROPIC_API_KEY to parse free-text orders)"))
    st.caption("Graph browser: [localhost:3000](http://localhost:3000)")
    st.caption("⚠️ Demo only. Not for clinical use. All patients are synthetic.")

tab_queue, tab_new, tab_patients, tab_graph = st.tabs(
    ["Pharmacist queue", "New order", "Patients", "Knowledge graph"])


# --------------------------------------------------------------------------- queue
def render_order(order_id: str):
    rep = order_report(order_id)
    p, d, rx, f, doc = rep["patient"], rep["drug"], rep["rx"], rep["formulation"], rep["prescriber"]
    blockers = [x for x in rep["findings"] if x["severity"] == "block"]

    st.subheader(f"{d.get('name')} for {p.get('name')}")
    dose = f"{rx.get('dose_mg')} mg" if rx.get("dose_mg") is not None else f"{rx.get('concentration_pct')}%"
    st.caption(f"Order {order_id} · {STATUS_LABEL.get(rep['order']['status'], rep['order']['status'])} · "
               f"Rx {dose}, {rx.get('frequency_per_day')}×/day for {rx.get('duration_days')} days ({rx.get('route')}) · "
               f"{doc.get('name', '')} · Patient {p.get('age_years')} y, {p.get('weight_kg')} kg")

    left, right = st.columns([3, 2])
    with left:
        if f:
            st.markdown("#### Proposed formulation")
            c1, c2, c3 = st.columns(3)
            c1.metric("Strength", f["concentration"])
            c2.metric("Make", f"{f['quantity']} {f['quantity_unit']}")
            c3.metric("Beyond-use date", f"{f['bud_days']} days")
            st.markdown(f"**{f['form']}** in **{f['base']}**  \n{f['dose_text']}")
            st.success(f"**Label:** {f['directions']}")
            st.caption(f"BUD source: {f['bud_source']}")
            with st.expander(f"Why not other bases? ({len(f.get('excluded') or [])} excluded)"):
                for e in f.get("excluded") or []:
                    st.markdown(f"- ❌ {e}")
                for a in f.get("alternatives") or []:
                    st.markdown(f"- ↪️ Alternative: {a}")
                if not f.get("excluded") and not f.get("alternatives"):
                    st.write("No other candidate bases.")
        else:
            st.warning("No formulation proposed.")

        st.markdown("#### Safety findings")
        if not rep["findings"]:
            st.success("No findings.")
        for x in rep["findings"]:
            box = SEVERITY_BOX.get(x["severity"], st.info)
            text = f"**{x['severity'].upper()} · {x['category']}** — {x['message']}"
            if x["evidence"]:
                text += "\n\n" + "\n".join(f"- `{e}`" for e in x["evidence"][:5])
            box(text)

    with right:
        st.markdown("#### Agent trace")
        for s in rep["steps"]:
            st.markdown(f"**{s['agent']}** · _{s['action']}_  \n{s['summary']}")

    st.markdown("#### Evidence graph")
    st.caption("What the agents looked at in FalkorDB: the patient's facts, the drug's classes, the chosen base, "
               "and the ingredient paths that ruled other bases out.")
    st.graphviz_chart(order_dot(order_id), use_container_width=True)
    st.markdown(" ".join(
        f"<span style='color:{c}'>■</span> <small>{'Excluded base' if k == 'Excluded' else k}</small>"
        for k, c in COLORS.items()), unsafe_allow_html=True)

    if llm.available() and st.button("Ask Claude for a pharmacist brief", key=f"brief_{order_id}"):
        with st.spinner("Claude is reading the agents' findings..."):
            try:
                brief = llm.summarize({k: rep[k] for k in ("patient", "drug", "rx", "formulation", "findings")})
                st.info(brief.summary + "\n\n" + "\n".join(f"- {a}" for a in brief.action_items))
            except Exception as e:  # show any API problem in the UI
                st.error(str(e))

    if rep["order"]["status"] == "AWAITING_REVIEW":
        st.markdown("#### Pharmacist decision")
        note = st.text_input("Note", key=f"note_{order_id}")
        override = True
        if blockers:
            override = st.checkbox(f"Override {len(blockers)} blocking finding(s) (requires documented reason)",
                                   key=f"ovr_{order_id}")
        a, b, c = st.columns(3)
        if a.button("Approve", type="primary", disabled=not (f and override and (not blockers or note)),
                    key=f"ok_{order_id}"):
            db.run(Q.APPROVE, {"order_id": order_id, "id": f"rev_{uuid.uuid4().hex[:8]}", "by": "pharmacist",
                               "note": note, "at": time.time()})
            st.rerun()
        if b.button("Reject", key=f"no_{order_id}"):
            db.run(Q.REJECT, {"order_id": order_id, "id": f"rev_{uuid.uuid4().hex[:8]}", "by": "pharmacist",
                              "note": note, "at": time.time()})
            st.rerun()
        if c.button("Re-run agents", key=f"rerun_{order_id}"):
            process(order_id, restart=True)
            st.rerun()

    if f:
        with st.expander("Report a reaction to an ingredient (the graph will remember it)"):
            ings = db.run("""MATCH (:Order {id: $o})-[:PROPOSED]->(:Formulation)-[:USES_BASE]->(:Base)-[:CONTAINS]->(e:Excipient)
                             RETURN e.id AS id, e.name AS name ORDER BY name""", {"o": order_id})
            choice = st.selectbox("Ingredient", ings, format_func=lambda r: r["name"], key=f"ing_{order_id}")
            what = st.text_input("What happened?", key=f"rx_note_{order_id}")
            if st.button("Save reaction", key=f"react_{order_id}") and choice:
                db.run(Q.REPORT_REACTION, {"patient_id": p["id"], "excipient_id": choice["id"],
                                           "note": what, "at": time.time()})
                st.success(f"Saved. Future orders for {p['name']} will avoid {choice['name']}.")


with tab_queue:
    orders = db.run(Q.LIST_ORDERS)
    if not orders:
        st.info("No orders yet. Load the demo data from the sidebar.")
    else:
        rows = [{"Order": o["order_id"], "Patient": o["patient"], "Drug": o["drug"],
                 "Status": STATUS_LABEL.get(o["status"], o["status"]), "Blockers": o["blockers"],
                 "Source": o["source"]} for o in orders]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        labels = {o["order_id"]: f"{o['patient']} · {o['drug']} · {STATUS_LABEL.get(o['status'], o['status'])}"
                  for o in orders}
        sel = st.selectbox("Open order", list(labels), format_func=labels.get)
        st.divider()
        render_order(sel)


# --------------------------------------------------------------------------- new order
with tab_new:
    st.markdown("#### Structured prescription")
    patients = db.run("MATCH (p:Patient) RETURN p.id AS id, p.name AS name ORDER BY name")
    doctors = db.run("MATCH (d:Prescriber) RETURN d.id AS id, d.name AS name ORDER BY name")
    drugs = db.run("MATCH (d:Drug) RETURN d.id AS id, d.name AS name ORDER BY name")
    if patients and doctors:
        with st.form("rx_form"):
            c1, c2, c3 = st.columns(3)
            pt = c1.selectbox("Patient", patients, format_func=lambda r: r["name"])
            dr = c2.selectbox("Prescriber", doctors, format_func=lambda r: r["name"])
            dg = c3.selectbox("Drug", drugs, format_func=lambda r: r["name"])
            c4, c5, c6, c7 = st.columns(4)
            route = c4.selectbox("Route", ["oral", "topical"])
            strength = c5.number_input("Dose (mg) or strength (%)", min_value=0.0, value=5.0, step=0.5)
            freq = c6.number_input("Times per day", 1, 6, 1)
            days = c7.number_input("Days", 1, 365, 30)
            qty = st.number_input("Quantity in grams (topicals only)", 0, 1000, 30)
            notes = st.text_input("Notes")
            if st.form_submit_button("Submit and run agents", type="primary"):
                rx_id = f"rx_{uuid.uuid4().hex[:8]}"
                add_prescription({"id": rx_id, "patient": pt["id"], "prescriber": dr["id"], "drug": dg["id"],
                                  "route": route, "dose_mg": strength if route == "oral" else None,
                                  "concentration_pct": strength if route == "topical" else None,
                                  "frequency_per_day": int(freq), "duration_days": int(days),
                                  "quantity": qty if route == "topical" else None, "notes": notes})
                oid = create_order(rx_id, source="manual entry")
                process(oid)
                st.success(f"Order {oid} processed. Open it in the Pharmacist queue.")

    st.markdown("#### Free-text order (parsed by Claude)")
    text = st.text_area("Paste an order", value=demo_patients.FREE_TEXT_EXAMPLE, height=100)
    if st.button("Parse and run agents", disabled=not llm.available()):
        oid = f"ord_{uuid.uuid4().hex[:8]}"
        db.run("CREATE (:Order {id: $id, status: 'RECEIVED', source: 'free text', raw_text: $t, created_at: $ts})",
               {"id": oid, "t": text, "ts": int(time.time())})
        with st.spinner("Claude is reading the order, then the agents take over..."):
            try:
                status = process(oid)
                st.success(f"Order {oid}: {STATUS_LABEL.get(status, status)}. Open it in the Pharmacist queue.")
            except Exception as e:
                st.error(str(e))
    if not llm.available():
        st.caption("Set ANTHROPIC_API_KEY to enable this.")


# --------------------------------------------------------------------------- patients
with tab_patients:
    patients = db.run("MATCH (p:Patient) RETURN p.id AS id, p.name AS name ORDER BY name")
    if patients:
        pt = st.selectbox("Patient", patients, format_func=lambda r: r["name"], key="pt_view")
        prof = db.run(Q.PATIENT_PROFILE, {"patient_id": pt["id"]})[0]
        pp = props(prof["p"])
        st.markdown(f"**{pp['name']}** · {pp['age_years']} y · {pp['weight_kg']} kg  \n_{pp.get('story', '')}_")
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Conditions**\n" + "\n".join(
            f"- {c['name']}{' _(derived)_' if c.get('derived') else ''}" for c in prof["conditions"] if c.get("name")))
        c2.markdown("**Allergies / avoids**\n" + "\n".join(f"- {a}" for a in prof["allergies"] + prof["avoids"]))
        c3.markdown("**Current meds**\n" + "\n".join(f"- {m}" for m in prof["meds"]))
        st.markdown("**Memory**  \nTolerated bases: " + (", ".join(prof["tolerated"]) or "none yet") +
                    "  \nPast reactions: " + (", ".join(prof["reactions"]) or "none"))

    with st.expander("Add a synthetic patient"):
        with st.form("new_patient"):
            name = st.text_input("Name")
            c1, c2 = st.columns(2)
            age = c1.number_input("Age (years)", 0.0, 120.0, 30.0)
            wt = c2.number_input("Weight (kg)", 1.0, 300.0, 70.0)
            conds = db.run("MATCH (c:Condition) RETURN c.id AS id, c.name AS name ORDER BY name")
            groups = db.run("""MATCH (x) WHERE x:DrugClass OR x:ExcipientGroup OR x:Excipient OR x:Drug
                               RETURN x.id AS id, x.name AS name ORDER BY name""")
            sel_c = st.multiselect("Conditions", conds, format_func=lambda r: r["name"])
            sel_a = st.multiselect("Allergies (drug, class, ingredient or ingredient group)", groups,
                                   format_func=lambda r: r["name"])
            sel_m = st.multiselect("Current medications", drugs, format_func=lambda r: r["name"])
            if st.form_submit_button("Add patient") and name:
                add_patient({"id": f"pt_{uuid.uuid4().hex[:8]}", "name": name, "age_years": age, "weight_kg": wt,
                             "conditions": [c["id"] for c in sel_c], "allergies": [a["id"] for a in sel_a],
                             "takes": [m["id"] for m in sel_m], "story": "Added in the app."})
                st.success(f"Added {name}.")


# --------------------------------------------------------------------------- knowledge graph
with tab_graph:
    st.markdown("The agents only reason through these Cypher queries (from `compounder/queries.py`).")
    names = ["CANDIDATE_BASES", "PREFERRED_FORMS", "INGREDIENT_ALLERGY_CONFLICTS", "INGREDIENT_CONDITION_CONFLICTS",
             "INGREDIENT_DRUG_INTERACTIONS", "DRUG_ALLERGY", "DRUG_CROSS_REACTIVITY", "DRUG_INTERACTIONS",
             "DRUG_CONDITION_CAUTIONS", "DOSE_RULE", "COMMERCIAL_PRODUCTS", "PATIENT_ORDER_HISTORY", "APPROVE",
             "REPORT_REACTION"]
    pick = st.selectbox("Query", names)
    st.code(getattr(Q, pick).strip(), language="cypher")

    st.markdown("#### Graph size")
    counts = db.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS nodes ORDER BY nodes DESC")
    rels = db.run("MATCH ()-[r]->() RETURN type(r) AS relationship, count(r) AS edges ORDER BY edges DESC")
    c1, c2 = st.columns(2)
    c1.dataframe(counts, hide_index=True, use_container_width=True)
    c2.dataframe(rels, hide_index=True, use_container_width=True)

    st.markdown("#### Read-only Cypher console")
    cy = st.text_area("Cypher", "MATCH (e:Excipient)-[:IS_A*1..3]->(g {id: 'azo_dye'})\nRETURN e.name AS dye", height=90)
    if st.button("Run query"):
        if any(w in cy.upper() for w in ("CREATE", "MERGE", "DELETE", "SET ", "REMOVE", "DROP")):
            st.error("Read-only console: write clauses are not allowed.")
        else:
            try:
                res = db.graph().ro_query(cy)
                cols = [h[1] for h in res.header]
                st.dataframe([dict(zip(cols, [str(v) if hasattr(v, "properties") else v for v in row]))
                              for row in res.result_set], use_container_width=True)
            except Exception as e:
                st.error(str(e))
