from app.services.session_service import (
    create_session,
    calculate_suspect_progress
)
from app.services.scenario_loader import load_scenario_from_json
from app.infra.db import SessionLocal
from app.infra.db_models import SecretModel, SessionSuspectStateModel


def test_calculate_suspect_progress():
    db = SessionLocal()

    # -------------------------
    # 1. Load sample scenario
    # -------------------------
    scenario = load_scenario_from_json("scenarios/piloto.json", db=db)

    # Pick first suspect
    suspect = scenario.suspects[0]
    suspect_id = suspect.id

    # -------------------------
    # 2. Create session
    # -------------------------
    session = create_session(scenario.id, db=db)
    session_id = session.id

    # -------------------------
    # 3. Get all core secrets of suspect
    # -------------------------
    core_secrets = db.query(SecretModel).filter(
        SecretModel.suspect_id == suspect_id,
        SecretModel.is_core == True
    ).all()

    assert len(core_secrets) > 0, "Test scenario must contain at least 1 core secret."

    # -------------------------
    # 4. Check initial progress = 0.0
    # -------------------------
    p_initial = calculate_suspect_progress(session_id, suspect_id, db=db)
    assert p_initial == 0.0, f"Expected progress=0.0 but got {p_initial}"

    # -------------------------
    # 5. Reveal FIRST core secret and recalc
    # -------------------------
    first_secret_id = core_secrets[0].id

    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id,
        SessionSuspectStateModel.suspect_id == suspect_id
    ).first()

    state.revealed_secret_ids.append(first_secret_id)
    db.commit()

    p_mid = calculate_suspect_progress(session_id, suspect_id, db=db)
    expected_mid = 1 / len(core_secrets)
    assert abs(p_mid - expected_mid) < 0.0001, (
        f"Expected {expected_mid}, got {p_mid}"
    )

    # -------------------------
    # 6. Reveal ALL core secrets and recalc
    # -------------------------
    for s in core_secrets:
        if s.id not in state.revealed_secret_ids:
            state.revealed_secret_ids.append(s.id)

    db.commit()

    p_full = calculate_suspect_progress(session_id, suspect_id, db=db)
    assert p_full == 1.0, f"Expected full progress=1.0 but got {p_full}"

    print("T21 test passed successfully!")


if __name__ == "__main__":
    test_calculate_suspect_progress()