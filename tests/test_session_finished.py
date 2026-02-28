import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.infra.db_models import Base, ScenarioModel, SuspectModel
from app.services.scenario_loader import load_scenario_from_json

# Same patching logic as test_happy_path_flow.py
import app.infra.db as db_module
import app.api.sessions as api_sessions
import app.services.chat_service as chat_service
import app.services.secret_service as secret_service
import app.services.session_service as session_service
import app.services.session_finalize_service as session_finalize_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)

db_module.engine = engine
db_module.SessionLocal = TestingSessionLocal
api_sessions.SessionLocal = TestingSessionLocal
chat_service.SessionLocal = TestingSessionLocal
secret_service.SessionLocal = TestingSessionLocal
session_service.SessionLocal = TestingSessionLocal
session_finalize_service.SessionLocal = TestingSessionLocal

Base.metadata.create_all(bind=engine)

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
            "evidence_ids": scenario.required_evidence_ids
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
