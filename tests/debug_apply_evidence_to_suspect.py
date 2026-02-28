from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.db_models import (
    Base,
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SecretModel,
    SessionModel,
    SessionSuspectStateModel
)
from app.services.secret_service import apply_evidence_to_suspect


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def setup_test_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return TestingSessionLocal()


def seed_basic_scenario(db):
    """
    Creates:
    - 1 scenario
    - 1 suspect
    - 2 evidences
    - 2 secrets (1 core, 1 non-core)
    - 1 session
    """
    scenario = ScenarioModel(title="Test Scenario")
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    suspect = SuspectModel(
        scenario_id=scenario.id,
        name="Suspect A"
    )
    db.add(suspect)
    db.commit()
    db.refresh(suspect)

    evidence_correct = EvidenceModel(
        scenario_id=scenario.id,
        name="Correct Evidence"
    )
    evidence_wrong = EvidenceModel(
        scenario_id=scenario.id,
        name="Wrong Evidence"
    )
    db.add_all([evidence_correct, evidence_wrong])
    db.commit()
    db.refresh(evidence_correct)
    db.refresh(evidence_wrong)

    secret_core = SecretModel(
        suspect_id=suspect.id,
        evidence_id=evidence_correct.id,
        content="Core secret revealed",
        is_core=True
    )
    secret_non_core = SecretModel(
        suspect_id=suspect.id,
        evidence_id=evidence_correct.id,
        content="Non-core secret revealed",
        is_core=False
    )
    db.add_all([secret_core, secret_non_core])
    db.commit()

    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    state = SessionSuspectStateModel(
        session_id=session.id,
        suspect_id=suspect.id,
        revealed_secret_ids=[],
        is_closed=False,
        progress=0.0
    )
    db.add(state)
    db.commit()

    return {
        "session_id": session.id,
        "suspect_id": suspect.id,
        "correct_evidence_id": evidence_correct.id,
        "wrong_evidence_id": evidence_wrong.id,
        "core_secret_id": secret_core.id,
        "non_core_secret_id": secret_non_core.id
    }


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_correct_evidence_reveals_secrets():
    """
    Positive case:
    - Correct evidence reveals both secrets linked to it.
    """
    db = setup_test_db()
    data = seed_basic_scenario(db)

    revealed = apply_evidence_to_suspect(
        session_id=data["session_id"],
        suspect_id=data["suspect_id"],
        evidence_id=data["correct_evidence_id"],
        db=db
    )

    revealed_ids = [s["secret_id"] for s in revealed]

    assert data["core_secret_id"] in revealed_ids
    assert data["non_core_secret_id"] in revealed_ids
    assert len(revealed_ids) == 2


def test_core_secret_updates_progress():
    """
    Positive case:
    - Revealing a core secret updates progress correctly.
    """
    db = setup_test_db()
    data = seed_basic_scenario(db)

    apply_evidence_to_suspect(
        session_id=data["session_id"],
        suspect_id=data["suspect_id"],
        evidence_id=data["correct_evidence_id"],
        db=db
    )

    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == data["session_id"],
        SessionSuspectStateModel.suspect_id == data["suspect_id"]
    ).first()

    assert state.progress == 1.0
    assert state.is_closed is True


def test_wrong_evidence_reveals_nothing():
    """
    Negative case:
    - Wrong evidence reveals no secrets.
    """
    db = setup_test_db()
    data = seed_basic_scenario(db)

    revealed = apply_evidence_to_suspect(
        session_id=data["session_id"],
        suspect_id=data["suspect_id"],
        evidence_id=data["wrong_evidence_id"],
        db=db
    )

    assert revealed == []

    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == data["session_id"],
        SessionSuspectStateModel.suspect_id == data["suspect_id"]
    ).first()

    assert state.revealed_secret_ids == []
    assert state.progress == 0.0
    assert state.is_closed is False
