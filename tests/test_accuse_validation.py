import pytest
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.main import app
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SessionModel,
    SessionEvidenceUsageModel
)

client = TestClient(app)

def test_cannot_accuse_invalid_suspect():
    import os
    from app.services.scenario_loader import load_scenario_from_json

    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        scenario = load_scenario_from_json(scenario_path, db=db)
        
        # create a dummy suspect in another scenario
        other_scenario = ScenarioModel(scenario_code="acc1", title="Dummy", culprit_id=999)
        db.add(other_scenario)
        db.flush()
        
        invalid_suspect = SuspectModel(scenario_id=other_scenario.id, name="Invalid")
        db.add(invalid_suspect)
        db.commit()
        
        scenario_id = scenario.id
        invalid_suspect_id = invalid_suspect.id
    finally:
        db.close()

    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    test_session_id = resp.json()["session_id"]

    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": invalid_suspect_id,
            "evidence_ids": [],
            "motive_key": "financial_gain"
        }
    )

    assert resp.status_code == 404
    assert "not found in scenario" in resp.json()["detail"]


def test_cannot_accuse_invalid_evidence():
    import os
    from app.services.scenario_loader import load_scenario_from_json

    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        scenario = load_scenario_from_json(scenario_path, db=db)
        marina = db.query(SuspectModel).filter(SuspectModel.name == "Marina Souza").first()
        
        # create a dummy evidence in another scenario
        other_scenario = ScenarioModel(scenario_code="acc2", title="Dummy", culprit_id=999)
        db.add(other_scenario)
        db.flush()
        
        invalid_evidence = EvidenceModel(scenario_id=other_scenario.id, name="Invalid")
        db.add(invalid_evidence)
        db.commit()
        
        scenario_id = scenario.id
        marina_id = marina.id
        invalid_evidence_id = invalid_evidence.id
    finally:
        db.close()

    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    test_session_id = resp.json()["session_id"]

    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": [invalid_evidence_id],
            "motive_key": "financial_gain"
        }
    )

    assert resp.status_code == 404
    assert "are invalid or do not belong to scenario" in resp.json()["detail"]


def test_cannot_accuse_with_unused_evidence():
    import os
    from app.services.scenario_loader import load_scenario_from_json

    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        scenario = load_scenario_from_json(scenario_path, db=db)
        marina = db.query(SuspectModel).filter(SuspectModel.name == "Marina Souza").first()
        relatorio = db.query(EvidenceModel).filter(EvidenceModel.scenario_id == scenario.id).first()
        
        scenario_id = scenario.id
        marina_id = marina.id
        relatorio_id = relatorio.id
    finally:
        db.close()

    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    test_session_id = resp.json()["session_id"]

    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": [relatorio_id],
            "motive_key": "financial_gain"
        }
    )

    assert resp.status_code == 409
    assert "was not used effectively during the session" in resp.json()["detail"]


def test_can_accuse_with_used_evidence():
    import os
    from app.services.scenario_loader import load_scenario_from_json

    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        scenario = load_scenario_from_json(scenario_path, db=db)
        marina = db.query(SuspectModel).filter(SuspectModel.name == "Marina Souza").first()
        relatorio = db.query(EvidenceModel).filter(EvidenceModel.scenario_id == scenario.id).first()
        
        scenario_id = scenario.id
        marina_id = marina.id
        relatorio_id = relatorio.id
    finally:
        db.close()

    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    test_session_id = resp.json()["session_id"]

    # Use a evidência no chat de forma eficaz (com contexto e a evidence correta)
    resp_chat = client.post(
        f"/sessions/{test_session_id}/suspects/{marina_id}/messages",
        json={"text": "Este rascunho de relatório não parece bater com o outro", "evidence_id": relatorio_id}
    )
    assert resp_chat.status_code == 200
    assert resp_chat.json()["evidence_effect"] == "revealed_secret"

    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": [relatorio_id],
            "motive_key": "financial_gain"
        }
    )

    # Pode falhar o julgamento, mas não deve dar 404 nem 409 de validação
    assert resp.status_code == 200
    assert resp.json()["result_type"] == "partial"
