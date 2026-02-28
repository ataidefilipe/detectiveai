from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import SessionModel
from app.services.verdict_service import evaluate_verdict
from app.core.exceptions import NotFoundError, RuleViolationError


def finalize_session(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Finalizes a game session:
    - Evaluates the verdict
    - Persists the result in the session
    - Marks the session as finished

    Returns:
        Dict with session_id, result_type and verdict details
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

        if session.status == "finished":
            raise RuleViolationError(f"Session {session_id} is already finished.")

        # ---------------------------------------
        # 2. Evaluate verdict
        # ----------------------------------------
        verdict = evaluate_verdict(
            session_id=session_id,
            chosen_suspect_id=chosen_suspect_id,
            evidence_ids=evidence_ids,
            db=db
        )

        # ----------------------------------------
        # 3. Persist result in session
        # ----------------------------------------
        session.chosen_suspect_id = chosen_suspect_id
        session.chosen_evidence_ids = evidence_ids or []
        session.result_type = verdict["result_type"]
        session.status = "finished"

        db.commit()
        db.refresh(session)

        # ----------------------------------------
        # 4. Return minimal useful data
        # ----------------------------------------
        return {
            "session_id": session.id,
            "status": session.status,
            "result_type": session.result_type,
            "verdict": verdict
        }

    finally:
        if close_session:
            db.close()
