import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, SessionModel, 
    SessionSuspectStateModel, EvidenceModel, SessionEvidenceUsageModel
)

client = TestClient(app)

@pytest.fixture
def setup_dossier_data():
    db = SessionLocal()
    scenario = ScenarioModel(scenario_code="dossier_test_case", title="Dossier Test Scenario")
    db.add(scenario)
    db.commit()

    suspect = SuspectModel(
        scenario_id=scenario.id,
        suspect_code="marina_souza",
        name="Marina Souza",
        role_title="Assistente Financeira",
        image_url="/static/assets/templates/suspect-template.svg",
        backstory="Assistente financeira da empresa.",
        claims=[],
        knowledge_items=[]
    )
    db.add(suspect)
    db.commit()

    evidence = EvidenceModel(
        scenario_id=scenario.id,
        evidence_code="ev_01",
        name="Caneca Quebrada",
        description="Fragmentos de cerâmica com café.",
        image_url="/static/assets/templates/evidence-template.svg"
    )
    db.add(evidence)
    db.commit()

    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.commit()

    state = SessionSuspectStateModel(
        session_id=session.id,
        suspect_id=suspect.id,
        stance="defensive",
        patience=45.0,
        pressure=15.0
    )
    db.add(state)
    db.commit()

    yield {
        "session_id": session.id,
        "suspect_id": suspect.id,
        "evidence_id": evidence.id,
        "db": db
    }

    db.close()


def test_list_session_suspects_dossier_fields(setup_dossier_data):
    session_id = setup_dossier_data["session_id"]
    suspect_id = setup_dossier_data["suspect_id"]

    res = client.get(f"/sessions/{session_id}/suspects")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0

    first = [s for s in data if s["suspect_id"] == suspect_id][0]
    assert first["role_title"] == "Assistente Financeira"
    assert first["image_url"].endswith(".svg")
    assert first["state"] is not None
    assert first["state"]["stance"] == "defensive"
    assert first["state"]["patience"] == 45.0
    assert isinstance(first["used_evidences"], list)


def test_get_suspect_dossier_endpoint(setup_dossier_data):
    session_id = setup_dossier_data["session_id"]
    suspect_id = setup_dossier_data["suspect_id"]

    res = client.get(f"/sessions/{session_id}/suspects/{suspect_id}/dossier")
    assert res.status_code == 200
    dossier = res.json()
    assert dossier["suspect_id"] == suspect_id
    assert dossier["name"] == "Marina Souza"
    assert dossier["role_title"] == "Assistente Financeira"

    # Testar 404 para suspeito inexistente
    res_404 = client.get(f"/sessions/{session_id}/suspects/999999/dossier")
    assert res_404.status_code == 404


def test_suspect_dossier_reflects_used_evidence(setup_dossier_data):
    session_id = setup_dossier_data["session_id"]
    suspect_id = setup_dossier_data["suspect_id"]
    evidence_id = setup_dossier_data["evidence_id"]
    db = setup_dossier_data["db"]

    # Simular uso de evidência
    usage = SessionEvidenceUsageModel(
        session_id=session_id,
        suspect_id=suspect_id,
        evidence_id=evidence_id,
        was_effective=True,
        effect_type="revealed_secret",
        times_presented=1
    )
    db.add(usage)
    db.commit()

    res = client.get(f"/sessions/{session_id}/suspects/{suspect_id}/dossier")
    assert res.status_code == 200
    dossier = res.json()
    assert len(dossier["used_evidences"]) == 1
    ev = dossier["used_evidences"][0]
    assert ev["evidence_id"] == evidence_id
    assert ev["name"] == "Caneca Quebrada"
    assert ev["was_effective"] is True
    assert ev["effect_type"] == "revealed_secret"
