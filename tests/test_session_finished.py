import os
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal
from app.main import app
from app.infra.db_models import Base, ScenarioModel, SuspectModel
from app.services.scenario_loader import load_scenario_from_json

def test_cannot_message_finished_session():
    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        load_scenario_from_json(scenario_path, db=db)
        scenario = db.query(ScenarioModel).first()
        marina = db.query(SuspectModel).filter(SuspectModel.name == "Marina Souza").first()
    finally:
        db.close()

    client = TestClient(app)

    # 1. Create session
    resp = client.post("/sessions", json={"scenario_id": scenario.id})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # 2. Accuse directly (which finishes the session)
    resp = client.post(
        f"/sessions/{session_id}/accuse",
        json={
            "suspect_id": marina.id,
            "evidence_ids": []
        }
    )
    assert resp.status_code == 200

    # 3. Try to send message
    resp = client.post(
        f"/sessions/{session_id}/suspects/{marina.id}/messages",
        json={"text": "Algo a dizer?"}
    )

    # 4. Should fail since it is finished
    assert resp.status_code == 409
    assert "is already finished" in resp.json()["detail"]
