import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal
from app.main import app
from app.infra.db_models import ScenarioModel, SuspectModel, EvidenceModel

client = TestClient(app)

def test_api_does_not_leak_internal_notes():
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(scenario_code="internal-test", title="Internal Note Test")
        db.add(scenario)
        db.flush()

        suspect = SuspectModel(
            scenario_id=scenario.id,
            name="Secret Suspect",
            internal_note="Player cannot read this."
        )
        evidence = EvidenceModel(
            scenario_id=scenario.id,
            name="Secret Evidence",
            internal_note="Player cannot read this either."
        )
        db.add_all([suspect, evidence])
        db.commit()

        scenario_id = scenario.id
    finally:
        db.close()

    res = client.post("/sessions", json={"scenario_id": scenario_id})
    assert res.status_code == 200
    session_id = res.json()["session_id"]

    res_suspects = client.get(f"/sessions/{session_id}/suspects")
    assert res_suspects.status_code == 200
    suspects = res_suspects.json()
    assert len(suspects) == 1
    assert "internal_note" not in suspects[0]

    res_evidences = client.get(f"/sessions/{session_id}/evidences")
    assert res_evidences.status_code == 200
    evidences = res_evidences.json()
    assert len(evidences) == 1
    assert "internal_note" not in evidences[0]
