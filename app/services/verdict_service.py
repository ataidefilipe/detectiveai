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
from app.core.telemetry import telemetry_logger
import json


def evaluate_verdict(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    motive_key: str,
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
            - chosen_motive_key
            - motive_result
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
            raise NotFoundError(f"Session {session_id} not found.")

        # ----------------------------------------
        # 2. Load scenario
        # ----------------------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        if not scenario:
            raise NotFoundError(
                f"Scenario {session.scenario_id} not found for session {session_id}."
            )

        real_culprit_id = scenario.culprit_id
        required_evidence_ids = scenario.required_evidence_ids or []
        true_motive_key = scenario.true_motive_key
        
        # Validate motive exists in scenario options
        if scenario.motive_options:
            valid_motive_keys = [m.get("key") for m in scenario.motive_options]
            if motive_key not in valid_motive_keys:
                raise NotFoundError(f"Motive {motive_key} is not valid for this scenario.")

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
            # T9: Changed to session-level (removed suspect_id == chosen_suspect_id).
            # T10: Added requirement for was_effective == True.
            used_evidences = db.query(SessionEvidenceUsageModel.evidence_id).filter(
                SessionEvidenceUsageModel.session_id == session_id,
                SessionEvidenceUsageModel.was_effective == True,
                SessionEvidenceUsageModel.evidence_id.in_(provided)
            ).all()
            used_evidence_ids = {row[0] for row in used_evidences}

            for ev_id in provided:
                if ev_id not in used_evidence_ids:
                    raise RuleViolationError(f"Evidence {ev_id} was not used effectively during the session.")

        # ----------------------------------------
        # 3. Assess Motive Result & Reason Codes
        # ----------------------------------------
        motive_result = "correct" if motive_key == true_motive_key else "wrong"
        
        # T11: Reason Codes
        reason_codes = []

        # ----------------------------------------
        # 4. Wrong culprit → immediate fail
        # ----------------------------------------
        if chosen_suspect_id != real_culprit_id:
            reason_codes.append("wrong_suspect")
            
            result_dict = {
                "result_type": "wrong",
                "missing_evidence_ids": required_evidence_ids,
                "required_evidence_ids": required_evidence_ids,
                "chosen_suspect_id": chosen_suspect_id,
                "real_culprit_id": real_culprit_id,
                "chosen_motive_key": motive_key,
                "motive_result": motive_result,
                "reason_codes": reason_codes
            }
            telemetry_logger.info(json.dumps({
                "event": "session_verdict",
                "session_id": session_id,
                "scenario_id": scenario.id,
                **result_dict
            }))
            return result_dict

        # ----------------------------------------
        # 5. Culprit correct → check evidences & motive
        # ----------------------------------------
        if motive_result == "wrong":
            reason_codes.append("wrong_motive")
            
        required = set(required_evidence_ids)
        missing = list(required - set(provided))
        
        if missing:
            reason_codes.append("missing_evidence")

        if not reason_codes:
            result_type = "correct"
        else:
            result_type = "partial"

        result_dict = {
            "result_type": result_type,
            "missing_evidence_ids": missing,
            "required_evidence_ids": required_evidence_ids,
            "chosen_suspect_id": chosen_suspect_id,
            "real_culprit_id": real_culprit_id,
            "chosen_motive_key": motive_key,
            "motive_result": motive_result,
            "reason_codes": reason_codes
        }
        
        telemetry_logger.info(json.dumps({
            "event": "session_verdict",
            "session_id": session_id,
            "scenario_id": scenario.id,
            **result_dict
        }))

        return result_dict

    finally:
        if close_session:
            db.close()
