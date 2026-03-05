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
    
