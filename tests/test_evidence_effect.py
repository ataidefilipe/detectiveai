from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from tests.conftest import TestingSessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, EvidenceModel, SecretModel, SessionModel, SessionSuspectStateModel
)
from unittest.mock import patch
from app.api.schemas.chat import StateTransitionResult, NpcShift, ConversationEffect

client = TestClient(app)

def test_evidence_effect_api():
    db = TestingSessionLocal()
    try:
        # Create minimal scenario data
        scenario = ScenarioModel(scenario_code="eff1", title="Effectiveness API Test")
        db.add(scenario)
        db.commit()

        suspect = SuspectModel(name="Test Suspect", scenario_id=scenario.id)
        evidence_good = EvidenceModel(name="Good Evidence", scenario_id=scenario.id)
        evidence_bad = EvidenceModel(name="Bad Evidence", scenario_id=scenario.id)
        db.add_all([suspect, evidence_good, evidence_bad])
        db.commit()

        secret = SecretModel(
            suspect_id=suspect.id,
            evidence_id=evidence_good.id,
            content="I am guilty"
        )
        db.add(secret)
        db.commit()

        # Create session
        response = client.post("/sessions", json={"scenario_id": scenario.id})
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 1. Turn with bad evidence (none effect)
        res_bad = client.post(
            f"/sessions/{session_id}/suspects/{suspect.id}/messages",
            json={"text": "Hello", "evidence_id": evidence_bad.id}
        )
        assert res_bad.status_code == 200
        data_bad = res_bad.json()
        assert data_bad["evidence_effect"] == "none"

        # 2. Turn with good evidence (reveals secret)
        res_good = client.post(
            f"/sessions/{session_id}/suspects/{suspect.id}/messages",
            json={"text": "Explain this!", "evidence_id": evidence_good.id}
        )
        assert res_good.status_code == 200
        data_good = res_good.json()
        assert data_good["evidence_effect"] == "revealed_secret"

        # 3. Turn with good evidence again (duplicate)
        res_dup = client.post(
            f"/sessions/{session_id}/suspects/{suspect.id}/messages",
            json={"text": "Explain this again!", "evidence_id": evidence_good.id}
        )
        assert res_dup.status_code == 200
        data_dup = res_dup.json()
        assert data_dup["evidence_effect"] == "duplicate"
        
        # 4. Turn with bad evidence but causing reaction (reaction_only)
        # Mocking the `resolve_turn_state` to force a pressured shift
        with patch("app.services.interrogation_turn_service.resolve_turn_state") as mock_resolve:
            mock_resolve.return_value = StateTransitionResult(
                conversation_effect=ConversationEffect.none,
                npc_shift=NpcShift.pressured,
                state_deltas={}
            )
            # using a new evidence as to not hit out_of_context or duplicate paths easily
            evidence_reaction = EvidenceModel(name="Reaction Evidence", scenario_id=scenario.id)
            db.add(evidence_reaction)
            db.commit()
            
            res_reaction = client.post(
                f"/sessions/{session_id}/suspects/{suspect.id}/messages",
                json={"text": "Aham!", "evidence_id": evidence_reaction.id}
            )
            assert res_reaction.status_code == 200
            data_reaction = res_reaction.json()
            assert data_reaction["evidence_effect"] == "reaction_only"
            assert data_reaction["narrative_feedback"]["suspect_reaction"] == "pressionado"

    finally:
        db.close()
