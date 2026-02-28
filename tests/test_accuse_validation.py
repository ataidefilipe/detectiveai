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
        other_scenario = ScenarioModel(title="Dummy", culprit_id=999)
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
            "evidence_ids": []
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
        other_scenario = ScenarioModel(title="Dummy", culprit_id=999)
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
            "evidence_ids": [invalid_evidence_id]
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
            "evidence_ids": [relatorio_id]
        }
    )

    assert resp.status_code == 409
    assert "was not used during the session" in resp.json()["detail"]


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

    # Use a evidência no chat
    resp_chat = client.post(
        f"/sessions/{test_session_id}/suspects/{marina_id}/messages",
        json={"text": "Explique isso.", "evidence_id": relatorio_id}
    )
    assert resp_chat.status_code == 200

    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": [relatorio_id]
        }
    )

    # Pode falhar o julgamento, mas não deve dar 404 nem 409 de validação
    assert resp.status_code == 200
    assert resp.json()["result_type"] == "partial"
