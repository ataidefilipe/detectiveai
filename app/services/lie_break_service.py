from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import logging
import json

logger = logging.getLogger(__name__)

from app.infra.db_models import (
    SessionSuspectStateModel,
    SuspectModel,
    EvidenceModel
)
from app.core.exceptions import NotFoundError

def evaluate_broken_lies(
    session_id: int,
    suspect_id: int,
    evidence_id: int,
    current_topics: Optional[List[str]] = None,
    last_topic_id: Optional[str] = None,
    db: Optional[Session] = None
) -> List[Dict[str, str]]:
    """
    Evaluates if the presented evidence breaks any of the suspect's lies
    under the current topic context.

    Returns a list of newly broken lies in the format:
    [{"id": "lie_id", "statement": "The lie text"}]
    """
    if db is None:
        raise ValueError("Database session is required to evaluate broken lies")

    # 1. Retrieve the suspect state
    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id,
        SessionSuspectStateModel.suspect_id == suspect_id
    ).first()

    if not state:
        raise NotFoundError(f"Suspect {suspect_id} state not found for session {session_id}")

    # 2. Retrieve the suspect to get their lies configuration
    suspect = db.query(SuspectModel).filter(
        SuspectModel.id == suspect_id
    ).first()

    if not suspect:
        raise NotFoundError(f"Suspect {suspect_id} not found")

    # If the suspect has no lies configured, nothing to break
    if not suspect.lies:
        return []

    # 3. Retrieve the presented evidence
    evidence = db.query(EvidenceModel).filter(
        EvidenceModel.id == evidence_id
    ).first()

    if not evidence:
        raise NotFoundError(f"Evidence {evidence_id} not found")

    # Normalize context topics
    active_topics = current_topics or []
    
    newly_broken_lies = []

    # 4. Iterate through suspect lies and evaluate conditions
    for lie in suspect.lies:
        # Pydantic schema validation when scenario loads ensures these fields exist
        lie_id = lie.get("id")
        lie_statement = lie.get("statement")
        broken_by_evidence_name = lie.get("broken_by_evidence")
        topic_id = lie.get("topic_id")

        if not lie_id or not broken_by_evidence_name:
            continue

        # Condition A: Has this lie been broken already?
        if lie_id in state.broken_lie_ids:
            continue

        # Condition B: Does the evidence match the required one?
        if evidence.name != broken_by_evidence_name:
            continue

        # Condition C: Is the context matching the lie's topic?
        is_context_matching = (topic_id in active_topics) or (topic_id == last_topic_id)
        if not is_context_matching:
            logger.debug(f"Lie {lie_id} requires topic {topic_id}, but context is: current={active_topics}, last={last_topic_id}")
            continue

        # All conditions met! The claim is broken.
        logger.info(json.dumps({
            "event": "lie_broken",
            "session_id": session_id,
            "suspect_id": suspect_id,
            "lie_id": lie_id,
            "evidence_name": evidence.name
        }))
        state.broken_lie_ids.append(lie_id)
        newly_broken_lies.append({
            "id": lie_id,
            "statement": lie_statement
        })

    # 5. Flush state to database
    if newly_broken_lies:
        # Use mutable list reassignment if SQLAlchemy doesn't track append correctly by default
        # or rely on MutableList.as_mutable configured in db_models.py
        db.flush()
        db.refresh(state)

    return newly_broken_lies
