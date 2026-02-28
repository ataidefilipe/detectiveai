import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.main import app
from tests.conftest import TestingSessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, EvidenceModel, SecretModel, SessionModel
)

client = TestClient(app)

def test_invariant_cannot_accuse_with_unused_evidence():
    """F1 - invariant: player cannot accuse using an evidence they never showed."""
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(title="Invariant Test Scenario")
        db.add(scenario)
        db.commit()

        suspect = SuspectModel(name="Test Suspect", scenario_id=scenario.id)
        db.add(suspect)

        evidence = EvidenceModel(name="Secret Weapon", scenario_id=scenario.id)
        db.add(evidence)
        db.commit()

        scenario.culprit_id = suspect.id
        scenario.required_evidence_ids = [evidence.id]
        db.commit()

        # Create session
        res = client.post("/sessions", json={"scenario_id": scenario.id})
        session_id = res.json()["session_id"]

        # Accuse directly without ever presenting evidence
        res_accuse = client.post(
            f"/sessions/{session_id}/accuse",
            json={"suspect_id": suspect.id, "evidence_ids": [evidence.id]}
        )

        assert res_accuse.status_code == 409
        assert "was not used" in res_accuse.json()["detail"]

    finally:
        db.close()


def test_invariant_cannot_play_in_finished_session():
    """F1 - invariant: session locked after sending accusation."""
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(title="Finished Session Scenario")
        db.add(scenario)
        db.commit()

        suspect = SuspectModel(name="Test Suspect", scenario_id=scenario.id)
        evidence = EvidenceModel(name="Test Evidence", scenario_id=scenario.id)
        db.add_all([suspect, evidence])
        db.commit()

        scenario.culprit_id = suspect.id
        scenario.required_evidence_ids = [evidence.id]
        db.commit()

        # Create session
        res = client.post("/sessions", json={"scenario_id": scenario.id})
        session_id = res.json()["session_id"]

        # Present the evidence once so it's allowed for accusation
        client.post(
            f"/sessions/{session_id}/suspects/{suspect.id}/messages",
            json={"text": "Take a look.", "evidence_id": evidence.id}
        )

        # Accuse -> finishes session
        res_accuse = client.post(
            f"/sessions/{session_id}/accuse",
            json={"suspect_id": suspect.id, "evidence_ids": [evidence.id]}
        )
        assert res_accuse.status_code == 200

        # Attempt to chat again (Zombie Session)
        res_chat = client.post(
            f"/sessions/{session_id}/suspects/{suspect.id}/messages",
            json={"text": "Im reviving the dead scenario!"}
        )

        assert res_chat.status_code == 409
        assert "is already finished" in res_chat.json()["detail"]

    finally:
        db.close()


def test_invariant_no_is_mandatory_spoiler_in_response():
    """F1 - invariant: evidence response must not leak the is_mandatory spoiler."""
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(title="Spoiler Test")
        db.add(scenario)
        db.commit()

        evidence = EvidenceModel(name="The Gun", scenario_id=scenario.id)
        db.add(evidence)
        db.commit()

        scenario.required_evidence_ids = [evidence.id]
        db.commit()

        res = client.post("/sessions", json={"scenario_id": scenario.id})
        session_id = res.json()["session_id"]

        res_ev = client.get(f"/sessions/{session_id}/evidences")
        assert res_ev.status_code == 200
        evidences = res_ev.json()
        assert len(evidences) == 1
        
        # is_mandatory should NOT be in the response dictionary
        assert "is_mandatory" not in evidences[0]

    finally:
        db.close()


@patch("app.services.interrogation_turn_service.add_npc_reply")
def test_invariant_atomic_turn_rollback_on_error(mock_add_npc_reply):
    """F1 - invariant: if a turn crashes mid-way (e.g. at the LLM adapter), the entire turn rolls back."""
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(title="Transaction Test")
        db.add(scenario)
        db.commit()

        suspect = SuspectModel(name="Test Suspect", scenario_id=scenario.id)
        db.add(suspect)
        db.commit()

        res = client.post("/sessions", json={"scenario_id": scenario.id})
        session_id = res.json()["session_id"]

        # Mock the NPC reply to throw an exception
        mock_add_npc_reply.side_effect = Exception("OpenAI servers down!")

        # The modern Starlette TestClient will raise unhandled exceptions correctly
        with pytest.raises(Exception, match="OpenAI servers down!"):
            res_msg = client.post(
                f"/sessions/{session_id}/suspects/{suspect.id}/messages",
                json={"text": "Did you do it?"}
            )

        # Validate that the player's message was NOT saved in the database
        session_obj = db.query(SessionModel).filter_by(id=session_id).first()
        messages_count = len(session_obj.chat_messages)
        
        # 0 messages are expected: the player's message should be rolled back and the DB stays clean.
        assert messages_count == 0

    finally:
        db.close()
