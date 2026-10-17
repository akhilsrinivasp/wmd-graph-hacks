"""End-to-end tests against a running FalkorDB (skipped if none is reachable).

Uses a separate graph name so it never touches the demo data.
"""
import os

import pytest

os.environ["COMPOUNDER_GRAPH"] = "compounder_test"

from compounder import db  # noqa: E402
from compounder import queries as Q  # noqa: E402
from compounder.agents.orchestrator import process  # noqa: E402
from compounder.report import order_report  # noqa: E402
from compounder.seed.loader import load_all  # noqa: E402


def _falkordb_up() -> bool:
    try:
        db.run("RETURN 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _falkordb_up(), reason="FalkorDB is not running")


@pytest.fixture(scope="module", autouse=True)
def seeded():
    load_all()
    yield
    db.graph().delete()


def run_rx(rx_id: str) -> dict:
    oid = db.run("MATCH (o:Order)-[:FILLS]->(:Prescription {id: $rx}) RETURN o.id AS id", {"rx": rx_id})[0]["id"]
    assert process(oid, restart=True) == "AWAITING_REVIEW"
    return order_report(oid)


def messages(rep, severity=None):
    return [f["message"] for f in rep["findings"] if severity is None or f["severity"] == severity]


def test_young_child_gets_liquid_without_azo_dyes():
    rep = run_rx("rx_1001")  # Maya, amlodipine, azo-dye allergy
    f = rep["formulation"]
    assert f["form"] == "Oral suspension"
    assert f["concentration"] == "1 mg/mL"
    assert "1.5 mL" in f["directions"]
    assert not messages(rep, "block")


def test_fructose_intolerance_excludes_sucrose_and_sorbitol_vehicles():
    rep = run_rx("rx_1003")  # Aisha, gabapentin, HFI
    base = rep["formulation"]["base"]
    assert "Starch-based" in base
    assert any("fructose" in e for e in rep["formulation"]["excluded"])


def test_pde5_with_nitrate_is_blocked():
    rep = run_rx("rx_1004")  # Robert, sildenafil + isosorbide mononitrate
    assert any("hypotension" in m for m in messages(rep, "block"))


def test_soy_allergy_excludes_plo_gel_and_flags_warfarin():
    rep = run_rx("rx_1005")  # Daniel, ketoprofen topical
    assert rep["formulation"]["base"] == "Hydrophilic ointment base"
    assert any("PLO" in e and "Soy" in e for e in rep["formulation"]["excluded"])
    assert any("Warfarin" in m for m in messages(rep, "warn"))


def test_weight_based_overdose_is_blocked():
    rep = run_rx("rx_1006")  # Sofia, metronidazole 500 mg TID at 20 kg
    assert any("75.0 mg/kg/day" in m for m in messages(rep, "block"))


def test_dye_lactose_gelatin_free_capsule():
    rep = run_rx("rx_1007")  # Ethan, levothyroxine
    f = rep["formulation"]
    assert "hypromellose" in f["base"]
    assert f["quantity"] == 90


def test_approval_and_reaction_are_remembered():
    rep = run_rx("rx_1001")
    oid = rep["order"]["id"]
    db.run(Q.APPROVE, {"order_id": oid, "id": "rev_t1", "by": "test", "note": "", "at": 0})
    tolerated = db.run("MATCH (:Patient {id: 'pt_maya'})-[:TOLERATED]->(b:Base) RETURN b.id AS id")
    assert {"id": "susp_sucrose"} in tolerated

    # A reaction to methylparaben must push the next formulation to a paraben-free base.
    db.run(Q.REPORT_REACTION, {"patient_id": "pt_maya", "excipient_id": "methylparaben", "note": "rash", "at": 0})
    rep2 = run_rx("rx_1001")
    assert "paraben-free" in rep2["formulation"]["base"]
