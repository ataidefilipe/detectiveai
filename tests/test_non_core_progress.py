from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from tests.conftest import TestingSessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, EvidenceModel, SecretModel, SessionModel, SessionSuspectStateModel
)

client = TestClient(app)

def test_non_core_progress_api():
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(title="Non Core Progress Test")
        db.add(scenario)
        db.commit()

        # Suspect 1: Only regular secrets (no core)
        suspect_regular = SuspectModel(name="Regular Suspect", scenario_id=scenario.id)
        # Suspect 2: No secrets at all
        suspect_empty = SuspectModel(name="Empty Suspect", scenario_id=scenario.id)
        
        db.add_all([suspect_regular, suspect_empty])
        db.commit()

        evidence_reg = EvidenceModel(name="Reg Evidence", scenario_id=scenario.id)
        db.add(evidence_reg)
        db.commit()

        secret_reg = SecretModel(
            suspect_id=suspect_regular.id,
            evidence_id=evidence_reg.id,
            content="I have a minor secret",
            is_core=False
        )
        db.add(secret_reg)
        db.commit()

        # Create session
        res_session = client.post("/sessions", json={"scenario_id": scenario.id})
        assert res_session.status_code == 200
        session_id = res_session.json()["session_id"]

        # Test Suspect 2: No secrets -> should start closed in state
        # Activating an empty suspect via their first turn should close them instantly.
        res_empty = client.post(
            f"/sessions/{session_id}/suspects/{suspect_empty.id}/messages",
            json={"text": "Hello"}
        )
        assert res_empty.status_code == 200
        data_empty = res_empty.json()
        assert data_empty["suspect_state"]["progress"] == 1.0
        assert data_empty["suspect_state"]["is_closed"] is True

        # Test Suspect 1: Starts at 0, goes to 1 after revealing the single non-core secret
        res_reg_start = client.post(
            f"/sessions/{session_id}/suspects/{suspect_regular.id}/messages",
            json={"text": "Hello"}
        )
        assert res_reg_start.status_code == 200
        # Progress starts at 0 since there's a non-core secret
        assert res_reg_start.json()["suspect_state"]["progress"] == 0.0

        res_reg_reveal = client.post(
            f"/sessions/{session_id}/suspects/{suspect_regular.id}/messages",
            json={"text": "Aha!", "evidence_id": evidence_reg.id}
        )
        assert res_reg_reveal.status_code == 200
        data_reg = res_reg_reveal.json()
        assert data_reg["suspect_state"]["progress"] == 1.0
        assert data_reg["suspect_state"]["is_closed"] is True

    finally:
        db.close()
