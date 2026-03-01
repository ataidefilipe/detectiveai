from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.session_service import get_suspect_state
from app.services.topic_state_service import get_topic_state
from app.infra.db_models import SessionModel, SuspectModel
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

    # Clamping
    return min(allowed_layer, max_layers)

def get_allowed_knowledge_facts(
    session_id: int, 
    suspect_id: int, 
    detected_topics: List[str], 
    db: Optional[Session] = None
) -> List[str]:
    """
    Iterates through all knowledge items of the suspect matching detected topics,
    evaluates their allowed layer, and concatenates the valid fact strings.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
        
    allowed_facts = []

    try:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
        if not suspect or not suspect.knowledge_items:
            return allowed_facts

        suspect_state = get_suspect_state(session_id, suspect_id, db)
        
        for k_item in suspect.knowledge_items:
            # We only evaluate facts for topics the player is currently asking about
            if k_item.get("topic_id") in detected_topics:
                # Get the state of this specifically demanded topic
                try:
                    topic_state = get_topic_state(session_id, suspect_id, k_item["topic_id"], db)
                except Exception:
                    # If topic state isn't found for some edge case, assume untouched defaults
                    topic_state = {"status": "untouched", "times_touched": 0, "sensitive_heat": 0.0}

                allowed_depth = evaluate_reveal_layer(k_item, suspect_state, topic_state)
                
                if allowed_depth > 0:
                    layers = k_item.get("content_layers", [])
                    # Append all layers up to the allowed depth
                    for i in range(allowed_depth):
                        allowed_facts.append(layers[i])

        return allowed_facts
    finally:
        if close_session:
            db.close()
