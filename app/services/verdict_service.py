from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    ScenarioModel
)


def evaluate_verdict(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Evaluates the final verdict of a session.

    Rules:
    - If chosen suspect is NOT the real culprit → result_type = "wrong"
    - If chosen suspect IS the real culprit:
        - If all required evidences are present → "correct"
        - Else → "partial"

    Returns:
        Dict with:
            - result_type
            - missing_evidence_ids
            - required_evidence_ids
            - chosen_suspect_id
            - real_culprit_id
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ----------------------------------------
        # 1. Load session
        # ----------------------------------------
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found.")

        # ----------------------------------------
        # 2. Load scenario
        # ----------------------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        if not scenario:
            raise ValueError(
                f"Scenario {session.scenario_id} not found for session {session_id}."
            )

        real_culprit_id = scenario.culprit_id
        required_evidence_ids = scenario.required_evidence_ids or []

        # ----------------------------------------
        # 3. Wrong culprit → immediate fail
        # ----------------------------------------
        if chosen_suspect_id != real_culprit_id:
            return {
                "result_type": "wrong",
                "missing_evidence_ids": required_evidence_ids,
                "required_evidence_ids": required_evidence_ids,
                "chosen_suspect_id": chosen_suspect_id,
                "real_culprit_id": real_culprit_id,
            }

        # ----------------------------------------
        # 4. Culprit correct → check evidences
        # ----------------------------------------
        provided = set(evidence_ids or [])
        required = set(required_evidence_ids)

        missing = list(required - provided)

        if not missing:
            result_type = "correct"
        else:
            result_type = "partial"

        return {
            "result_type": result_type,
            "missing_evidence_ids": missing,
            "required_evidence_ids": required_evidence_ids,
            "chosen_suspect_id": chosen_suspect_id,
            "real_culprit_id": real_culprit_id,
        }

    finally:
        if close_session:
            db.close()
