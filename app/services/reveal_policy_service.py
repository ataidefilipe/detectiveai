from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.session_service import get_suspect_state
from app.services.topic_state_service import get_topic_state
from app.infra.db_models import SessionModel, SuspectModel, SessionSuspectKnowledgeStateModel
from app.infra.db import SessionLocal


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
    rapport = suspect_state.get("rapport", 0.0)
    
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
        if patience > 30.0:
            allowed_layer = 1
        
        # Further pressure or rapport unlocks deeper layers
        if (pressure > 50.0 or rapport > 50.0) and times_touched > 1:
            allowed_layer = 2
        
        # Push to max if really pushing
        if pressure > 80.0 and times_touched > 2:
            allowed_layer = 3

    # Adjust based on kind and reliability
    if kind == "lie":
        # Harder to reveal a lie unless pushed significantly
        if pressure < 60.0:
            allowed_layer = 0
    elif kind == "rumor" or reliability == "low":
        # Limit layers for rumors unless extreme pressure/rapport is achieved
        if pressure < 80.0 and rapport < 80.0:
            allowed_layer = min(allowed_layer, 2)
    elif kind == "observed" and reliability == "high":
        # Solid direct observations are easier to bring up
        if allowed_layer >= 1 and (pressure > 40.0 or rapport > 40.0):
            allowed_layer = min(allowed_layer + 1, max_layers)

    # Clamping
    return min(allowed_layer, max_layers)


def get_allowed_knowledge_facts(
    session_id: int, 
    suspect_id: int, 
    detected_topics: List[str], 
    db: Optional[Session] = None
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

        suspect_state = get_suspect_state(session_id, suspect_id, db)
        
        for k_item in suspect.knowledge_items:
            # We only evaluate facts for topics the player is currently asking about
            if k_item.get("topic_id") in detected_topics:
                # Get the state of this specifically demanded topic
                knowledge_id = k_item.get("id")
                try:
                    topic_state = get_topic_state(session_id, suspect_id, k_item["topic_id"], db)
                except Exception:
                    # If topic state isn't found for some edge case, assume untouched defaults
                    topic_state = {"status": "untouched", "times_touched": 0, "sensitive_heat": 0.0}

                allowed_depth = evaluate_reveal_layer(k_item, suspect_state, topic_state)
                
                if allowed_depth > 0:
                    layers = k_item.get("content_layers", [])
                    max_available = len(layers)
                    
                    # Fetch persistence of knowledge state
                    k_state = None
                    if knowledge_id:
                        k_state = db.query(SessionSuspectKnowledgeStateModel).filter(
                            SessionSuspectKnowledgeStateModel.session_id == session_id,
                            SessionSuspectKnowledgeStateModel.suspect_id == suspect_id,
                            SessionSuspectKnowledgeStateModel.knowledge_id == str(knowledge_id)
                        ).first()
                        
                    current_depth = k_state.max_revealed_depth if k_state else 0
                    
                    allowed_clamped = min(allowed_depth, max_available)
                    
                    # Known knowledge (already revealed up to current_depth)
                    for i in range(min(current_depth, allowed_clamped)):
                        result["known_knowledge"].append(layers[i])
                        
                    # New knowledge
                    if allowed_clamped > current_depth:
                        for i in range(current_depth, allowed_clamped):
                            result["new_knowledge_this_turn"].append(layers[i])
                            
                        # Persist new depth
                        if knowledge_id:
                            if not k_state:
                                k_state = SessionSuspectKnowledgeStateModel(
                                    session_id=session_id,
                                    suspect_id=suspect_id,
                                    knowledge_id=str(knowledge_id),
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
