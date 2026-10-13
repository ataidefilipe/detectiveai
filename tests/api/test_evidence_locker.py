import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, SessionModel, 
    EvidenceModel, SessionEvidenceUsageModel
)

client = TestClient(app)

@pytest.fixture
def setup_evidence_locker_data():
    db = SessionLocal()
    scenario = ScenarioModel(scenario_code="ev_locker_test_case", title="Evidence Locker Scenario")
    db.add(scenario)
    db.commit()

    suspect = SuspectModel(
        scenario_id=scenario.id,
        suspect_code="rogerio_lima",
        name="Rogério Lima",
        role_title="Segurança Patrimonial",
        claims=[],
        knowledge_items=[]
    )
    db.add(suspect)
    db.commit()

    evidence1 = EvidenceModel(
        scenario_id=scenario.id,
        evidence_code="ev_01",
        name="Log de Câmeras",
        description="Reinicialização suspeita do gravador."
    )
    evidence2 = EvidenceModel(
        scenario_id=scenario.id,
        evidence_code="ev_02",
        name="Luvas Descartáveis",
        description="Luvas com resíduo de café na lixeira."
    )
    db.add_all([evidence1, evidence2])
    db.commit()

    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.commit()

    yield {
        "session_id": session.id,
        "suspect_id": suspect.id,
        "evidence1_id": evidence1.id,
        "evidence2_id": evidence2.id,
        "db": db
    }

    db.close()


def test_get_session_evidences_default_status(setup_evidence_locker_data):
    session_id = setup_evidence_locker_data["session_id"]

    res = client.get(f"/sessions/{session_id}/evidences")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2

    for ev in data:
        assert "evidence_code" in ev
        assert "image_url" in ev
        assert "is_used" in ev
        assert "usages" in ev
        assert isinstance(ev["usages"], list)
        assert ev["is_used"] is False


def test_get_session_evidences_with_usage(setup_evidence_locker_data):
    session_id = setup_evidence_locker_data["session_id"]
    suspect_id = setup_evidence_locker_data["suspect_id"]
    evidence1_id = setup_evidence_locker_data["evidence1_id"]
    db = setup_evidence_locker_data["db"]

    # Simular uso da evidência 1 com Rogério
    usage = SessionEvidenceUsageModel(
        session_id=session_id,
        suspect_id=suspect_id,
        evidence_id=evidence1_id,
        was_effective=True,
        effect_type="broke_claim",
        times_presented=2
    )
    db.add(usage)
    db.commit()

    res = client.get(f"/sessions/{session_id}/evidences")
    assert res.status_code == 200
    data = res.json()

    ev1 = [e for e in data if e["id"] == evidence1_id][0]
    assert ev1["is_used"] is True
    assert len(ev1["usages"]) == 1
    u = ev1["usages"][0]
    assert u["suspect_id"] == suspect_id
    assert u["suspect_name"] == "Rogério Lima"
    assert u["was_effective"] is True
    assert u["effect_type"] == "broke_claim"
    assert u["times_presented"] == 2
