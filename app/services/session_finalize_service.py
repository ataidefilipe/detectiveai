from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import SessionModel, NpcChatMessageModel, VerdictLogModel
from app.services.verdict_service import evaluate_verdict
from app.core.exceptions import NotFoundError, RuleViolationError


def finalize_session(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    motive_key: str,
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
            motive_key=motive_key,
            db=db
        )

        # ----------------------------------------
        # 3. Persist result in session
        # ----------------------------------------
        session.chosen_suspect_id = chosen_suspect_id
        session.chosen_evidence_ids = evidence_ids or []
        session.result_type = verdict["result_type"]
        session.status = "finished"

        # Analytics: registro do veredito
        turns_per_suspect = dict(
            db.query(NpcChatMessageModel.suspect_id, func.count(NpcChatMessageModel.id))
            .filter(
                NpcChatMessageModel.session_id == session_id,
                NpcChatMessageModel.sender_type == "player"
            )
            .group_by(NpcChatMessageModel.suspect_id)
            .all()
        )
        db.add(VerdictLogModel(
            session_id=session_id,
            scenario_id=session.scenario_id,
            result_type=verdict["result_type"],
            chosen_suspect_id=chosen_suspect_id,
            real_culprit_id=verdict.get("real_culprit_id"),
            chosen_motive_key=motive_key,
            motive_result=verdict.get("motive_result"),
            evidence_ids=evidence_ids or [],
            verdict=verdict,
            session_summary={
                "duration_seconds": int((datetime.now() - session.created_at).total_seconds()) if session.created_at else None,
                "total_turns": sum(turns_per_suspect.values()),
                "turns_per_suspect": {str(k): v for k, v in turns_per_suspect.items()},
            },
        ))

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
