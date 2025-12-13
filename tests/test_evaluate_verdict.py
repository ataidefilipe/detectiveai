from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.db_models import (
    Base,
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SessionModel
)
from app.services.verdict_service import evaluate_verdict


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def setup_test_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return TestingSessionLocal()


def seed_verdict_scenario(db):
    """
    Creates:
    - 1 scenario
    - 2 suspects
    - 2 mandatory evidences
    - 1 session
    """
    scenario = ScenarioModel(
        title="Verdict Test Scenario",
        required_evidence_ids=[]
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    suspect_guilty = SuspectModel(
        scenario_id=scenario.id,
        name="Guilty Suspect"
    )
    suspect_wrong = SuspectModel(
        scenario_id=scenario.id,
        name="Wrong Suspect"
    )
    db.add_all([suspect_guilty, suspect_wrong])
    db.commit()
    db.refresh(suspect_guilty)
    db.refresh(suspect_wrong)

    # Define culprit
    scenario.culprit_id = suspect_guilty.id
    db.commit()

    evidence_1 = EvidenceModel(
        scenario_id=scenario.id,
        name="Evidence 1"
    )
    evidence_2 = EvidenceModel(
        scenario_id=scenario.id,
        name="Evidence 2"
    )
    db.add_all([evidence_1, evidence_2])
    db.commit()
    db.refresh(evidence_1)
    db.refresh(evidence_2)

    # Persist mandatory evidences
    scenario.required_evidence_ids = [evidence_1.id, evidence_2.id]
    db.commit()

    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "culprit_id": suspect_guilty.id,
        "wrong_suspect_id": suspect_wrong.id,
        "evidence_1_id": evidence_1.id,
        "evidence_2_id": evidence_2.id
    }


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_verdict_wrong_culprit():
    """
    Case 1:
    - Wrong suspect accused → result_type = 'wrong'
    """
    db = setup_test_db()
    data = seed_verdict_scenario(db)

    result = evaluate_verdict(
        session_id=data["session_id"],
        chosen_suspect_id=data["wrong_suspect_id"],
        evidence_ids=[data["evidence_1_id"], data["evidence_2_id"]],
        db=db
    )

    assert result["result_type"] == "wrong"
    assert result["chosen_suspect_id"] == data["wrong_suspect_id"]
    assert result["real_culprit_id"] == data["culprit_id"]


def test_verdict_correct_with_all_evidences():
    """
    Case 2:
    - Correct suspect
    - All mandatory evidences provided
    → result_type = 'correct'
    """
    db = setup_test_db()
    data = seed_verdict_scenario(db)

    result = evaluate_verdict(
        session_id=data["session_id"],
        chosen_suspect_id=data["culprit_id"],
        evidence_ids=[data["evidence_1_id"], data["evidence_2_id"]],
        db=db
    )

    assert result["result_type"] == "correct"
    assert result["missing_evidence_ids"] == []


def test_verdict_partial_missing_evidence():
    """
    Case 3:
    - Correct suspect
    - Missing one mandatory evidence
    → result_type = 'partial'
    """
    db = setup_test_db()
    data = seed_verdict_scenario(db)

    result = evaluate_verdict(
        session_id=data["session_id"],
        chosen_suspect_id=data["culprit_id"],
        evidence_ids=[data["evidence_1_id"]],  # missing evidence_2
        db=db
    )

    assert result["result_type"] == "partial"
    assert data["evidence_2_id"] in result["missing_evidence_ids"]
