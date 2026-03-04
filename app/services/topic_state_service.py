from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db_models import SessionSuspectTopicStateModel
from app.infra.db import SessionLocal
from app.core.exceptions import NotFoundError

def get_topic_state(
    session_id: int, 
    suspect_id: int, 
    topic_id: str, 
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Fetches the state of a specific topic for a suspect in a session.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        topic_state = db.query(SessionSuspectTopicStateModel).filter(
            SessionSuspectTopicStateModel.session_id == session_id,
            SessionSuspectTopicStateModel.suspect_id == suspect_id,
            SessionSuspectTopicStateModel.topic_id == topic_id
        ).first()

        if not topic_state:
            raise NotFoundError(
                f"Topic state '{topic_id}' not found for suspect {suspect_id} in session {session_id}."
            )

        return {
            "topic_id": topic_state.topic_id,
            "status": topic_state.status,
            "times_touched": topic_state.times_touched,
            "sensitive_heat": topic_state.sensitive_heat
        }
    finally:
        if close_session:
            db.close()


def update_topic_hit(
    session_id: int,
    suspect_id: int,
    topic_id: str,
    heat_delta: float = 0.0,
    new_status: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Increments times_touched and optionally updates heat and status.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        topic_state = db.query(SessionSuspectTopicStateModel).filter(
            SessionSuspectTopicStateModel.session_id == session_id,
            SessionSuspectTopicStateModel.suspect_id == suspect_id,
            SessionSuspectTopicStateModel.topic_id == topic_id
        ).first()

        if not topic_state:
            raise NotFoundError(
                f"Topic state '{topic_id}' not found for suspect {suspect_id} in session {session_id}."
            )

        topic_state.times_touched += 1
        
        if heat_delta != 0.0:
            topic_state.sensitive_heat = max(0.0, min(100.0, topic_state.sensitive_heat + heat_delta))
            
        if new_status:
            topic_state.status = new_status
        elif topic_state.status == "untouched":
            topic_state.status = "touched"

        if close_session:
            db.commit()
            db.refresh(topic_state)
        else:
            db.flush()

        return {
            "topic_id": topic_state.topic_id,
            "status": topic_state.status,
            "times_touched": topic_state.times_touched,
            "sensitive_heat": topic_state.sensitive_heat
        }
    except Exception:
        if close_session:
            db.rollback()
        raise
    finally:
        if close_session:
            db.close()
