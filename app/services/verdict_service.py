from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SessionEvidenceUsageModel
)
from app.core.exceptions import NotFoundError, RuleViolationError


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
        # 2.5. Validate User Input (B2)
        # ----------------------------------------
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == chosen_suspect_id,
            SuspectModel.scenario_id == scenario.id
        ).first()

        if not suspect:
            raise NotFoundError(f"Suspect {chosen_suspect_id} not found in scenario {scenario.id}.")

        provided = list(set(evidence_ids or []))
        
        if provided:
            valid_evidences = db.query(EvidenceModel).filter(
                EvidenceModel.id.in_(provided),
                EvidenceModel.scenario_id == scenario.id
            ).all()

            if len(valid_evidences) != len(provided):
                raise NotFoundError(f"One or more evidence ids are invalid or do not belong to scenario {scenario.id}.")

            # ----------------------------------------
            # 2.6. Validate Evidence Usage (B3)
            # ----------------------------------------
            used_evidences = db.query(SessionEvidenceUsageModel.evidence_id).filter(
                SessionEvidenceUsageModel.session_id == session_id,
                SessionEvidenceUsageModel.evidence_id.in_(provided)
            ).all()
            used_evidence_ids = {row[0] for row in used_evidences}

            for ev_id in provided:
                if ev_id not in used_evidence_ids:
                    raise RuleViolationError(f"Evidence {ev_id} was not used during the session.")

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
        required = set(required_evidence_ids)

        missing = list(required - set(provided))

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
