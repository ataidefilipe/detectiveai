from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_service import get_suspect_state, update_suspect_state_from_deltas
from app.services.topic_state_service import update_topic_hit
from app.services.reveal_policy_service import get_allowed_knowledge_facts
from app.services.message_analysis_service import analyze_message
from app.services.turn_resolution_service import resolve_turn_state
from app.infra.db_models import SessionEvidenceUsageModel, SessionModel, ScenarioModel, NpcChatMessageModel
from app.api.schemas.chat import (
    MessageAnalysisResult,
    StateTransitionResult,
    TopicSignal,
    TurnDebugTrace
)
from app.core.config import settings


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

    # Fetch recent player messages for novelty check
    recent_player_msgs = [
        row[0] for row in db.query(NpcChatMessageModel.text).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id,
            NpcChatMessageModel.sender_type == "player",
            NpcChatMessageModel.id < player_msg["id"]
        ).order_by(NpcChatMessageModel.id.desc()).limit(3).all()
    ]

    # 1.2 Analyze player message against known topics
    msg_analysis = analyze_message(text, available_topics=available_topics, player_history=recent_player_msgs)

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
        # Verifica se o tópico ESPECÍFICO detectado é sensível 
        is_sens_hit = topic_id in msg_analysis.sensitive_topic_ids
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
    evidence_effect = "none"
    was_previously_used = False
    
    if evidence_id is not None:
        revealed_secrets, evidence_effect = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=evidence_id,
            detected_topics=msg_analysis.detected_topic_ids,
            db=db
        )
        
        # Penalize for out_of_context
        if evidence_effect == "out_of_context":
            update_suspect_state_from_deltas(
                session_id=session_id,
                suspect_id=suspect_id,
                deltas={"patience": -10.0},
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
            was_previously_used = False
            usage = SessionEvidenceUsageModel(
                session_id=session_id,
                suspect_id=suspect_id,
                evidence_id=evidence_id,
                was_effective=is_effective
            )
            db.add(usage)
        else:
            was_previously_used = True
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
        evidence_effect=evidence_effect,
        db=db
    )

    # 4. Fetch updated suspect state (snapshot for UX)
    suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )

    # Calculate evidence effect for UI feedback
    if evidence_id is not None:
        if evidence_effect not in ("out_of_context", "revealed_secret"):
            # Se a evidência não foi reveladora agora, e não bateu na trave do contexto,
            # mas ela já existia no histórico de uso (usage table) ANTES deste turno, então é duplicate.
            if was_previously_used:
                evidence_effect = "duplicate"
                
    # Feedback Sistêmico (Epic G)
    hints = []
    t_signal = TopicSignal.none

    # Se usou evidência fora de escopo
    if evidence_effect == "out_of_context":
        hints.append("evidência fora de contexto")
    
    # Sensibilidade
    if msg_analysis.sensitivity_hit.value in ["high", "medium"]:
        if state_transition.npc_shift.value in ["more_cooperative", "pressured"]:
            hints.append("tema sensível tocado adequadamente")
            t_signal = TopicSignal.strong
        elif state_transition.npc_shift.value == "more_defensive":
            hints.append("suspeito recuou ao tocar em tema sensível")
            t_signal = TopicSignal.weak
    else:
        # Se detectou algum tópico normal
        if msg_analysis.detected_topic_ids:
            t_signal = TopicSignal.good
            if state_transition.conversation_effect.value == "repeat":
                hints.append("tópico já explorado")
                t_signal = TopicSignal.weak

    # Se não detectou nada ("None" ou topics vazios)
    if not msg_analysis.detected_topic_ids and evidence_id is None:
        hints.append("pergunta muito vaga")
        t_signal = TopicSignal.weak

    debug_trace = None
    if settings.DEBUG_TURN_TRACE:
        debug_trace = TurnDebugTrace(
            message_analysis=msg_analysis,
            state_transition=state_transition,
            allowed_knowledge=allowed_knowledge
        )

    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "evidence_effect": evidence_effect,
        "suspect_state": suspect_state,
        "message_analysis": msg_analysis,
        "state_transition": state_transition,
        "conversation_effect": state_transition.conversation_effect.value,
        "npc_shift": state_transition.npc_shift.value,
        "topic_signal": t_signal,
        "feedback_hints": hints,
        "debug_trace": debug_trace
    }
