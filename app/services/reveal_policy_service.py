from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.session_service import get_suspect_state
from app.services.topic_state_service import get_topic_state
from app.infra.db_models import (
    SessionModel,
    SuspectModel,
    SessionSuspectKnowledgeStateModel,
    SessionClaimStateModel,
)
from app.infra.db import SessionLocal
from app.core.config import settings


def evaluate_reveal_layer(
    knowledge_item: Dict[str, Any],
    suspect_state: Dict[str, Any],
    topic_state: Dict[str, Any]
) -> int:
    """
    Evaluates the maximum allowed knowledge layer for a specific item
    given the current relational state and topic state.
    Returns an index (0 to N) representing how many elements of `content_layers` can be revealed.
    """
    patience = suspect_state.get("patience", 50.0)
    pressure = suspect_state.get("pressure", 0.0)
    # rapport removido (AI-003): campo dormant, nunca usado nas condicionais de reveal layer
    
    times_touched = topic_state.get("times_touched", 0)
    status = topic_state.get("status", "untouched")
    
    kind = knowledge_item.get("kind", "factual")
    reliability = knowledge_item.get("reliability", "high")
    
    max_layers = len(knowledge_item.get("content_layers", []))
    if max_layers == 0:
        return 0

    # MVP Heuristics
    allowed_layer = 0
    
    # Needs to be touched at least once to even talk about it specifically
    if status != "untouched" and times_touched > 0:
        if patience > settings.REVEAL_LAYER_1_PATIENCE_MIN:
            allowed_layer = 1
        
        # Further pressure unlocks deeper layers
        if pressure > settings.REVEAL_LAYER_2_PRESSURE_MIN and times_touched > 1:
            allowed_layer = 2
        
        # Push to max if really pushing
        if pressure > settings.REVEAL_LAYER_3_PRESSURE_MIN and times_touched > 2:
            allowed_layer = 3

    # Adjust based on kind and reliability
    if kind == "lie":
        # Harder to reveal a lie unless pushed significantly
        if pressure < 60.0:
            allowed_layer = 0
    elif kind == "rumor" or reliability == "low":
        # Limit layers for rumors unless extreme pressure is achieved
        if pressure < settings.REVEAL_LAYER_3_PRESSURE_MIN:
            allowed_layer = min(allowed_layer, 2)
    elif kind == "observed" and reliability == "high":
        # Solid direct observations are easier to bring up
        if allowed_layer >= 1 and pressure > 40.0:
            allowed_layer = min(allowed_layer + 1, max_layers)

    # Clamping
    return min(allowed_layer, max_layers)


def get_allowed_knowledge_facts(
    session_id: int, 
    suspect_id: int, 
    detected_topics: List[str], 
    db: Optional[Session] = None,
    suspect_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[str]]:
    """
    Iterates through all knowledge items of the suspect matching detected topics,
    evaluates their allowed layer, and categorizes facts as known or new.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
        
    result = {
        "known_knowledge": [],
        "new_knowledge_this_turn": []
    }

    try:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
        if not suspect or not suspect.knowledge_items:
            return result

        if suspect_state is None:
            suspect_state = get_suspect_state(session_id, suspect_id, db)

        # Map knowledge_ids gated behind reveal_on_break of active (unbroken) claims
        raw_claims = suspect.claims if isinstance(getattr(suspect, "claims", None), list) else []
        gated_by_claims: Dict[str, set] = {}
        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            cid = str(claim.get("claim_id", claim.get("id", ""))).strip()
            if not cid:
                continue
            for reward in claim.get("reveal_on_break", []) or []:
                rkid = str(reward.get("id")) if isinstance(reward, dict) else str(reward)
                if rkid:
                    gated_by_claims.setdefault(rkid, set()).add(cid)

        broken_claim_ids: set = set()
        if gated_by_claims:
            claim_states = (
                db.query(SessionClaimStateModel)
                .filter(
                    SessionClaimStateModel.session_id == session_id,
                    SessionClaimStateModel.suspect_id == suspect_id,
                    SessionClaimStateModel.status == "broken",
                )
                .all()
            )
            broken_claim_ids = {str(cs.claim_id) for cs in (claim_states or [])}

        # At most 1 new knowledge advancement per topic per turn (progressive reveal)
        new_revealed_topics: set = set()

        for k_item in suspect.knowledge_items:
            # We only evaluate facts for topics the player is currently asking about
            topic_id = k_item.get("topic_id")
            if topic_id in detected_topics:
                # Get the state of this specifically demanded topic
                knowledge_id = k_item.get("id")
                kid_str = str(knowledge_id) if knowledge_id else ""
                is_locked_by_active_claim = bool(
                    kid_str
                    and kid_str in gated_by_claims
                    and not (gated_by_claims[kid_str] & broken_claim_ids)
                )

                try:
                    topic_state = get_topic_state(session_id, suspect_id, topic_id, db)
                except Exception:
                    topic_state = {"status": "untouched", "times_touched": 0}

                allowed_depth = 0 if is_locked_by_active_claim else evaluate_reveal_layer(
                    k_item, suspect_state, topic_state
                )

                layers = k_item.get("content_layers", [])
                max_available = len(layers)

                # Fetch persistence of knowledge state (only if already needed)
                k_state = None
                if knowledge_id and (allowed_depth > 0 or is_locked_by_active_claim):
                    k_state = db.query(SessionSuspectKnowledgeStateModel).filter(
                        SessionSuspectKnowledgeStateModel.session_id == session_id,
                        SessionSuspectKnowledgeStateModel.suspect_id == suspect_id,
                        SessionSuspectKnowledgeStateModel.knowledge_id == kid_str
                    ).first()

                current_depth = k_state.max_revealed_depth if k_state else 0
                allowed_clamped = min(max(allowed_depth, current_depth), max_available)

                # Known knowledge (already revealed up to current_depth)
                for i in range(min(current_depth, allowed_clamped)):
                    result["known_knowledge"].append(layers[i])

                # New knowledge (only if unlocked and topic hasn't already revealed a new item this turn)
                if (
                    not is_locked_by_active_claim
                    and allowed_clamped > current_depth
                    and topic_id not in new_revealed_topics
                ):
                    for i in range(current_depth, allowed_clamped):
                        result["new_knowledge_this_turn"].append(layers[i])
                    new_revealed_topics.add(topic_id)

                    # Persist new depth
                    if knowledge_id:
                        if not k_state:
                            k_state = SessionSuspectKnowledgeStateModel(
                                session_id=session_id,
                                suspect_id=suspect_id,
                                knowledge_id=kid_str,
                                max_revealed_depth=allowed_clamped
                            )
                            db.add(k_state)
                        else:
                            k_state.max_revealed_depth = allowed_clamped
                        # flush is fine, but overall transaction commits at turn level
                        db.flush()

        return result
    finally:
        if close_session:
            db.close()
