from sqlalchemy.orm import Session
from tests.conftest import TestingSessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, EvidenceModel, SecretModel, SessionModel, SessionSuspectStateModel, SessionEvidenceUsageModel
)
from app.services.interrogation_turn_service import run_interrogation_turn

def test_evidence_was_effective_flag():
    db = TestingSessionLocal()
    try:
        # Create minimal scenario data
        scenario = ScenarioModel(title="Effectiveness Test")
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
        session = SessionModel(scenario_id=scenario.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        db.refresh(suspect)
        db.refresh(evidence_good)
        db.refresh(evidence_bad)

        state = SessionSuspectStateModel(session_id=session.id, suspect_id=suspect.id)
        db.add(state)
        db.commit()

        # 1. Turn with bad evidence (no secrets)
        run_interrogation_turn(
            session_id=session.id, suspect_id=suspect.id, text="...", evidence_id=evidence_bad.id, db=db
        )

        bad_usage = db.query(SessionEvidenceUsageModel).filter_by(
            session_id=session.id, suspect_id=suspect.id, evidence_id=evidence_bad.id
        ).first()

        assert bad_usage is not None
        assert bad_usage.was_effective is False

        # 2. Turn with good evidence (reveals secret)
        run_interrogation_turn(
            session_id=session.id, suspect_id=suspect.id, text="...", evidence_id=evidence_good.id, db=db
        )

        good_usage = db.query(SessionEvidenceUsageModel).filter_by(
            session_id=session.id, suspect_id=suspect.id, evidence_id=evidence_good.id
        ).first()

        assert good_usage is not None
        assert good_usage.was_effective is True

        # 3. Turn with good evidence again (no NEW secrets)
        run_interrogation_turn(
            session_id=session.id, suspect_id=suspect.id, text="Again...", evidence_id=evidence_good.id, db=db
        )

        good_usage_again = db.query(SessionEvidenceUsageModel).filter_by(
            session_id=session.id, suspect_id=suspect.id, evidence_id=evidence_good.id
        ).first()

        # Should remain true, not overwritten to false
        assert good_usage_again.was_effective is True

    finally:
        db.close()
