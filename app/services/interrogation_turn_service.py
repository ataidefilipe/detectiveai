from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_service import get_suspect_state, update_suspect_state_from_deltas
from app.services.topic_state_service import update_topic_hit
from app.services.reveal_policy_service import get_allowed_knowledge_facts
from app.services.message_analysis_service import analyze_message
from app.services.turn_resolution_service import resolve_turn_state
from app.infra.db_models import SessionEvidenceUsageModel, SessionModel, ScenarioModel


def run_interrogation_turn(
    session_id: int,
    suspect_id: int,
    text: str,
    evidence_id: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Orchestrates a full interrogation turn in a transactional manner.
    Expects an active database session and does not commit it.
    """

    # 1. Player message
    player_msg = add_player_message(
        session_id=session_id,
        suspect_id=suspect_id,
        text=text,
        evidence_id=evidence_id,
        db=db
    )

    # 1.1 Fetch current suspect conversational state
    initial_suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )

    # Fetch scenario topics to pass into message analysis
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    scenario = db.query(ScenarioModel).filter(ScenarioModel.id == session.scenario_id).first()
    available_topics = scenario.topics if scenario and scenario.topics else []

    # 1.2 Analyze player message against known topics
    msg_analysis = analyze_message(text, available_topics=available_topics)

    # 1.3 Resolve turn mechanics (State Transition)
    state_transition = resolve_turn_state(
        analysis=msg_analysis,
        current_state=initial_suspect_state
    )

    # 1.4 Apply state deltas to DB
    if state_transition.state_deltas:
        update_suspect_state_from_deltas(
            session_id=session_id,
            suspect_id=suspect_id,
            deltas=state_transition.state_deltas,
            db=db
        )

    # 1.5 Update topic hits
    for topic_id in msg_analysis.detected_topic_ids:
        # Check if it was this topic that caused the sensitive hit (MVP simplified check)
        is_sens_hit = msg_analysis.sensitivity_hit.value == "high" 
        # Optional: could check if this *specific* topic is sensitive from available_topics
        heat_delta = 15.0 if is_sens_hit else 0.0

        update_topic_hit(
            session_id=session_id,
            suspect_id=suspect_id,
            topic_id=topic_id,
            heat_delta=heat_delta,
            db=db
        )

    # 2. Evidence logic (may reveal secrets)
    revealed_secrets = []
    if evidence_id is not None:
        revealed_secrets = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=evidence_id,
            db=db
        )

        # Log evidence usage and update was_effective if applicable
        usage = db.query(SessionEvidenceUsageModel).filter(
            SessionEvidenceUsageModel.session_id == session_id,
            SessionEvidenceUsageModel.suspect_id == suspect_id,
            SessionEvidenceUsageModel.evidence_id == evidence_id
        ).first()

        is_effective = len(revealed_secrets) > 0

        if not usage:
            usage = SessionEvidenceUsageModel(
                session_id=session_id,
                suspect_id=suspect_id,
                evidence_id=evidence_id,
                was_effective=is_effective
            )
            db.add(usage)
        else:
            if is_effective and not usage.was_effective:
                usage.was_effective = True
        
        db.flush()

    # 2.5 Extract Allowed Knowledge Layers based on Topics Touched
    allowed_knowledge = get_allowed_knowledge_facts(
        session_id=session_id,
        suspect_id=suspect_id,
        detected_topics=msg_analysis.detected_topic_ids,
        db=db
    )

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"],
        msg_analysis=msg_analysis,
        state_transition=state_transition,
        revealed_now=revealed_secrets,
        allowed_knowledge=allowed_knowledge,
        db=db
    )

    # 4. Fetch updated suspect state (snapshot for UX)
    suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )

    # Calculate evidence effect for UI feedback
    evidence_effect = "none"
    if evidence_id is not None:
        if is_effective:
            evidence_effect = "revealed_secret"
        elif usage and usage.was_effective:
            evidence_effect = "duplicate"

    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "evidence_effect": evidence_effect,
        "suspect_state": suspect_state,
        "message_analysis": msg_analysis,
        "state_transition": state_transition
    }
