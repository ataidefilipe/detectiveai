import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infra.db import SessionLocal, Base, init_db
from app.infra.db_models import ScenarioModel, SessionModel
from app.services.scenario_loader import load_scenario_from_json
import os

client = TestClient(app)

@pytest.fixture
def test_scenario():
    db = SessionLocal()
    try:
        scenario_path = os.path.join(os.path.dirname(__file__), "../../scenarios/piloto.json")
        scenario_obj = load_scenario_from_json(scenario_path, db=db)
        return scenario_obj.id
    finally:
        db.close()


def test_get_session_overview_includes_motives(test_scenario):
    # 1. Create a session using the loaded scenario
    response = client.post("/sessions", json={"scenario_id": test_scenario})
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # 2. Get session overview
    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    
    data = response.json()
    
    # 3. Assert motive_options are present in scenario overview
    assert "scenario" in data
    assert "motive_options" in data["scenario"]
    
    motive_options = data["scenario"]["motive_options"]
    assert len(motive_options) > 0
    
    # Just check if the structure is somewhat correct based on Piloto.json
    motive_keys = [m["key"] for m in motive_options]
    assert "financial_gain" in motive_keys
    assert "revenge" in motive_keys


def test_list_sessions(test_scenario):
    # 1. Create a session
    post_res = client.post("/sessions", json={"scenario_id": test_scenario})
    assert post_res.status_code == 200
    created_id = post_res.json()["session_id"]

    # 2. Call GET /sessions
    res = client.get("/sessions")
    assert res.status_code == 200
    sessions = res.json()
    assert isinstance(sessions, list)
    assert len(sessions) > 0

    # 3. Check created session exists in list
    matching = [s for s in sessions if s["id"] == created_id]
    assert len(matching) == 1
    session_item = matching[0]
    assert session_item["scenario_id"] == test_scenario
    assert "scenario_title" in session_item
    assert session_item["status"] == "in_progress"
    assert "messages_count" in session_item
    
