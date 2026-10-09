from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_service import get_suspect_state, update_suspect_state_from_deltas
from app.services.topic_state_service import update_topic_hit, get_topic_state
from app.services.reveal_policy_service import get_allowed_knowledge_facts
from app.services.message_analysis_service import analyze_message
from app.services.turn_resolution_service import resolve_turn_state
from app.services.turn_feedback_service import build_turn_feedback, build_narrative_feedback
from app.services.claim_resolution_service import resolve_broken_claims
from app.services.conversation_context_service import build_conversation_context
from app.services.move_classification_service import classify_move
from app.infra.db_models import (
    SessionEvidenceUsageModel, SessionModel, ScenarioModel, 
    NpcChatMessageModel, SuspectModel, SessionSuspectKnowledgeStateModel,
    SessionClaimStateModel, TurnLogModel
)
from fastapi.encoders import jsonable_encoder
from app.api.schemas.chat import (
    MessageAnalysisResult,
    StateTransitionResult,
    TopicSignal,
    TurnDebugTrace
)
from app.core.config import settings
from app.core.telemetry import telemetry_logger
import json


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

    # 1.0 Build conversation context (BEFORE analysis — provides topic inheritance)
    conversation_context = build_conversation_context(
        session_id=session_id,
        suspect_id=suspect_id,
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
    
    suspect_model = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
    suspect_profile = suspect_model.profile if suspect_model else None

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
    # Sprint 1 T1.2: Build semantic context for classifier
    from app.services.semantic_context_builder import build_semantic_analysis_context

    semantic_ctx = build_semantic_analysis_context(
        session_id=session_id,
        suspect_id=suspect_id,
        scenario=scenario,
        suspect=suspect_model,
        conversation_memory=conversation_context,
        db=db,
    )

    msg_analysis = analyze_message(
        text,
        available_topics=available_topics,
        player_history=recent_player_msgs,
        claims=semantic_ctx["public_claims"],
        evidences=semantic_ctx["public_evidences"],
        suspect_state=semantic_ctx["suspect_state"],
        active_topic_id=semantic_ctx["active_topic_id"],
    )

    # 1.2.5 Resolve move_type: GPT tem precedência, com validação (T1.4)
    if msg_analysis.move_type:
        from app.api.schemas.chat import MoveType
        try:
            move_type = MoveType(msg_analysis.move_type)
        except ValueError:
            # move_type do GPT não é um MoveType válido — mapear tipos semânticos
            _semantic_to_move = {
                "confront_claim": MoveType.pressure,
                "confront_evidence": MoveType.confront_evidence,
                "explore": MoveType.explore,
                "deepen": MoveType.deepen,
                "pressure": MoveType.pressure,
                "calm": MoveType.calm,
                "accuse_in_chat": MoveType.accuse_soft,
                "clarify": MoveType.deepen,
                "off_topic": MoveType.continue_flow,
            }
            move_type = _semantic_to_move.get(msg_analysis.move_type, classify_move(
                analysis=msg_analysis,
                context=conversation_context,
                evidence_id=evidence_id,
            ))

        # Validação pós-resolução
        if evidence_id is not None and move_type == MoveType.explore:
            move_type = MoveType.confront_evidence
        if msg_analysis.target_claim_ids and move_type not in (MoveType.pressure, MoveType.confront_evidence):
            move_type = MoveType.pressure
    else:
        move_type = classify_move(
            analysis=msg_analysis,
            context=conversation_context,
            evidence_id=evidence_id,
        )


    # 1.3 Resolve turn mechanics (State Transition)
    primary_topic_state = None
    if msg_analysis.primary_topic_id:
        try:
            primary_topic_state = get_topic_state(
                session_id=session_id,
                suspect_id=suspect_id,
                topic_id=msg_analysis.primary_topic_id,
                db=db
            )
        except Exception:
            pass # Ignora se não achar estado anterior
            
    state_transition = resolve_turn_state(
        analysis=msg_analysis,
        current_state=initial_suspect_state,
        topic_state=primary_topic_state,
        move_type=move_type,
        suspect_profile=suspect_profile
    )

    # T6: Persist primary_topic_id as last_topic_id for short-term context.
    # Preserve the existing last_topic_id if this turn didn't detect a new primary topic.
    new_last_topic_id = msg_analysis.primary_topic_id if msg_analysis.primary_topic_id else initial_suspect_state.get("last_topic_id")
    if new_last_topic_id:
        if not state_transition.state_deltas:
            state_transition.state_deltas = {}
        state_transition.state_deltas["last_topic_id"] = new_last_topic_id

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
        update_topic_hit(
            session_id=session_id,
            suspect_id=suspect_id,
            topic_id=topic_id,
            db=db
        )

    # 2. Evidence logic (may reveal secrets or break claims)
    revealed_secrets = []
    evidence_effect = "none"
    was_previously_used = False
    
    # 2.1 Check for newly broken claims (conversational or evidence)
    newly_broken_claims, claim_rewards = resolve_broken_claims(
        session_id=session_id,
        suspect_id=suspect_id,
        evidence_id=evidence_id,
        analysis=msg_analysis,
        conversation_memory=conversation_context,
        db=db
    )
    # TODO MVP-004: se claim_rewards tiver IDs de knowledge, injetá-los
    
    if evidence_id is not None:
        revealed_secrets, evidence_effect = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=evidence_id,
            conversation_memory=conversation_context,
            detected_topics=msg_analysis.detected_topic_ids,
            referenced_evidence_ids=msg_analysis.referenced_evidence_ids,  # NOVO
            target_claim_ids=msg_analysis.target_claim_ids,                # NOVO
            db=db
        )
        
        # Penalize for out_of_context
        if evidence_effect == "out_of_context":
            # MVP-004: Atenuate penalty if topic is sensitive
            penalty = settings.OUT_OF_CONTEXT_PENALTY_DEFAULT
            if msg_analysis.sensitivity_hit.value in ["high", "medium"]:
                penalty = settings.OUT_OF_CONTEXT_PENALTY_SENSITIVE
                
            update_suspect_state_from_deltas(
                session_id=session_id,
                suspect_id=suspect_id,
                deltas={"patience": penalty},
                db=db
            )

        # Log evidence usage and update was_effective if applicable
        usage = db.query(SessionEvidenceUsageModel).filter(
            SessionEvidenceUsageModel.session_id == session_id,
            SessionEvidenceUsageModel.suspect_id == suspect_id,
            SessionEvidenceUsageModel.evidence_id == evidence_id
        ).first()

        # Determinar effect_type
        def _resolve_effect_type(evidence_effect, newly_broken_claims, was_contextual):
            if not was_contextual:
                return "out_of_context"
            if evidence_effect == "revealed_secret":
                return "revealed_secret"
            if newly_broken_claims:
                return "broke_claim"
            if evidence_effect == "reaction_only":
                return "reaction_only"
            if evidence_effect == "duplicate":
                return "duplicate"
            return "none"

        is_effective = len(revealed_secrets) > 0 or len(newly_broken_claims) > 0
        was_contextual = evidence_effect != "out_of_context"
        effect_type = _resolve_effect_type(evidence_effect, newly_broken_claims, was_contextual)

        if not usage:
            was_previously_used = False
            usage = SessionEvidenceUsageModel(
                session_id=session_id,
                suspect_id=suspect_id,
                evidence_id=evidence_id,
                was_effective=is_effective,
                was_contextual=was_contextual,
                effect_type=effect_type,
                times_presented=1,
            )
            db.add(usage)
        else:
            was_previously_used = True
            from datetime import datetime
            usage.times_presented += 1
            usage.last_used_at = datetime.now()
            if is_effective and not usage.was_effective:
                usage.was_effective = True
            if was_contextual:
                usage.was_contextual = True
            usage.effect_type = effect_type  # último efeito prevalece
        
        db.flush()

    # 2.5 Extract Allowed Knowledge Layers based on Topics Touched
    # Use pre-turn patience baseline so this turn's sensitive topic penalty does not retroactively
    # block the introductory knowledge layer of the topic being asked.
    post_turn_suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )
    eval_state = {
        **post_turn_suspect_state,
        "patience": max(
            initial_suspect_state.get("patience", 50.0),
            post_turn_suspect_state.get("patience", 50.0)
        ),
        "pressure": max(
            initial_suspect_state.get("pressure", 0.0),
            post_turn_suspect_state.get("pressure", 0.0)
        ),
    }
    knowledge_facts = get_allowed_knowledge_facts(
        session_id=session_id,
        suspect_id=suspect_id,
        detected_topics=msg_analysis.detected_topic_ids,
        db=db,
        suspect_state=eval_state
    )
    allowed_knowledge = knowledge_facts.get("known_knowledge", [])
    new_knowledge = knowledge_facts.get("new_knowledge_this_turn", [])

    # 2.55 Reveal Claims for Detected Topics (Task 4.3)
    if msg_analysis.detected_topic_ids:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
        if suspect and suspect.claims:
            claim_ids_to_reveal = [
                c.get("claim_id") for c in suspect.claims 
                if c.get("topic_id") in msg_analysis.detected_topic_ids
            ]
            if claim_ids_to_reveal:
                db.query(SessionClaimStateModel).filter(
                    SessionClaimStateModel.session_id == session_id,
                    SessionClaimStateModel.suspect_id == suspect_id,
                    SessionClaimStateModel.claim_id.in_(claim_ids_to_reveal),
                    SessionClaimStateModel.is_revealed == False
                ).update({"is_revealed": True}, synchronize_session=False)
                db.flush()

    # MVP-004: Force reveal knowledge from claim_rewards (Sprint 3 T3.3)
    if claim_rewards:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
        if suspect and suspect.knowledge_items:
            # Map reward list to dict for easier lookup
            reward_map = {}
            for r in claim_rewards:
                if isinstance(r, dict):
                    reward_map[str(r.get("id"))] = r.get("depth")
                else:
                    reward_map[str(r)] = None # None means reveal all layers

            for k_item in suspect.knowledge_items:
                kid = str(k_item.get("id"))
                if kid in reward_map:
                    max_depth_target = reward_map[kid]
                    layers = k_item.get("content_layers", [])
                    
                    k_state = db.query(SessionSuspectKnowledgeStateModel).filter(
                        SessionSuspectKnowledgeStateModel.session_id == session_id,
                        SessionSuspectKnowledgeStateModel.suspect_id == suspect_id,
                        SessionSuspectKnowledgeStateModel.knowledge_id == kid
                    ).first()
                    
                    if k_state:
                        current_depth = k_state.max_revealed_depth
                        if max_depth_target is None:
                            new_depth = len(layers)
                        else:
                            new_depth = max(current_depth, min(max_depth_target, len(layers)))
                        
                        if new_depth > current_depth:
                            # Adicionar as novas camadas reveladas ao new_knowledge para o prompt
                            for i in range(current_depth, new_depth):
                                if layers[i] not in new_knowledge:
                                    new_knowledge.append(layers[i])
                            k_state.max_revealed_depth = new_depth
                        db.flush()
                    else:
                        # Se não existe estado, cria um com a profundidade alvo
                        new_depth = len(layers) if max_depth_target is None else min(max_depth_target, len(layers))
                        k_state = SessionSuspectKnowledgeStateModel(
                            session_id=session_id,
                            suspect_id=suspect_id,
                            knowledge_id=kid,
                            max_revealed_depth=new_depth
                        )
                        db.add(k_state)
                        for i in range(new_depth):
                            if layers[i] not in new_knowledge:
                                new_knowledge.append(layers[i])
                        db.flush()

    # AI-002: Build list of message IDs where evidence was effective so prompt_builder can pin them
    effective_usages = db.query(SessionEvidenceUsageModel).filter(
        SessionEvidenceUsageModel.session_id == session_id,
        SessionEvidenceUsageModel.suspect_id == suspect_id,
        SessionEvidenceUsageModel.was_effective == True
    ).all()
    effective_evidence_ids = {u.evidence_id for u in effective_usages}
    effective_message_ids = [
        row[0] for row in db.query(NpcChatMessageModel.id).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id,
            NpcChatMessageModel.sender_type == "player",
            NpcChatMessageModel.evidence_id.in_(effective_evidence_ids)
        ).all()
    ] if effective_evidence_ids else []

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"],
        msg_analysis=msg_analysis,
        state_transition=state_transition,
        revealed_now=revealed_secrets,
        allowed_knowledge=allowed_knowledge,
        new_knowledge_this_turn=new_knowledge,
        evidence_effect=evidence_effect,
        newly_broken_claims=newly_broken_claims,
        effective_message_ids=effective_message_ids,
        db=db
    )
    ai_trace = npc_msg.pop("ai_trace", None) or {}

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
            else:
                # MVP-002: Reação Sem Revelação (reaction_only)
                is_sensitive = any(t in msg_analysis.sensitive_topic_ids for t in msg_analysis.detected_topic_ids)
                has_reaction = state_transition.npc_shift.value in ["more_defensive", "pressured"]
                
                if is_sensitive or has_reaction:
                    evidence_effect = "reaction_only"
                
    # ── Sprint 3 T2.3 / Parecer Astra: Consolidar efeitos e precedências ────
    if newly_broken_claims:
        mechanical_effect = "broke_claim"
    elif revealed_secrets:
        mechanical_effect = "revealed_secret"
    elif evidence_effect in ("revealed_secret", "broke_claim", "out_of_context", "reaction_only", "duplicate"):
        mechanical_effect = evidence_effect
    else:
        mechanical_effect = "none"

    narrative_effect = "suspect_reacted_defensively" if state_transition.npc_shift.value in ("more_defensive", "pressured") else "no_reaction"
    # ───────────────────────────────────────────────────────────────────
                
    # Histórico recente de guidances para anti-spam / cooldown (últimos 3 turnos)
    recent_logs = db.query(TurnLogModel).filter(
        TurnLogModel.session_id == session_id,
        TurnLogModel.suspect_id == suspect_id
    ).order_by(TurnLogModel.id.desc()).limit(3).all()

    recent_guidances = []
    for log in recent_logs:
        if log.effects and isinstance(log.effects, dict):
            n_fb = log.effects.get("narrative_feedback")
            if isinstance(n_fb, dict) and n_fb.get("guidance"):
                recent_guidances.append(n_fb["guidance"])

    # Feedback Sistêmico (Epic G) via service extraído com precedência mecânica
    t_signal, hints = build_turn_feedback(
        analysis=msg_analysis,
        transition=state_transition,
        evidence_effect=evidence_effect,
        topic_state=primary_topic_state,
        newly_broken_claims=newly_broken_claims,
        revealed_secrets=revealed_secrets,
    )
    
    # Narrative Feedback (MVP-001) com supressão em conquistas e anti-spam
    narrative_fb = build_narrative_feedback(
        npc_shift=state_transition.npc_shift.value,
        topic_signal=t_signal,
        evidence_effect=evidence_effect,
        hints=hints,
        newly_broken_claims=newly_broken_claims,
        revealed_secrets=revealed_secrets,
        recent_guidances=recent_guidances,
    )

    debug_trace = None
    if settings.DEBUG_TURN_TRACE:
        debug_trace = TurnDebugTrace(
            message_analysis=msg_analysis,
            state_transition=state_transition,
            allowed_knowledge=allowed_knowledge,
            new_knowledge_this_turn=new_knowledge
        )

    # Analytics: um registro por turno, na mesma transação do turno
    previous_turns = db.query(TurnLogModel).filter(
        TurnLogModel.session_id == session_id,
        TurnLogModel.suspect_id == suspect_id
    ).count()
    render_ctx = ai_trace.get("render_context") or {}
    db.add(TurnLogModel(
        session_id=session_id,
        suspect_id=suspect_id,
        turn_number=previous_turns + 1,
        player_message_id=player_msg["id"],
        npc_message_id=npc_msg["id"],
        player_text=text,
        npc_text=npc_msg["text"],
        evidence_id=evidence_id,
        intent=msg_analysis.intent.value,
        move_type=move_type.value,
        primary_topic_id=msg_analysis.primary_topic_id,
        analysis_provider=msg_analysis.analysis_provider,
        evidence_effect=evidence_effect,
        response_mode=render_ctx.get("response_mode"),
        state_before=jsonable_encoder(initial_suspect_state),
        state_after=jsonable_encoder(suspect_state),
        analysis=jsonable_encoder(msg_analysis),
        transition=jsonable_encoder(state_transition),
        effects=jsonable_encoder({
            "revealed_secrets": revealed_secrets,
            "newly_broken_claims": newly_broken_claims,
            "claim_rewards": claim_rewards,
            "allowed_knowledge": allowed_knowledge,
            "new_knowledge_this_turn": new_knowledge,
            "evidence_was_previously_used": was_previously_used,
            "mechanical_effect": mechanical_effect,
            "narrative_effect": narrative_effect,
            "topic_signal": t_signal,
            "feedback_hints": hints,
            "narrative_feedback": narrative_fb,
            "conversation_context": conversation_context,
            "semantic_context": semantic_ctx,
            "effective_message_ids": effective_message_ids,
        }),
        ai=jsonable_encoder({k: v for k, v in ai_trace.items() if k != "prompt"}),
        prompt=jsonable_encoder(ai_trace.get("prompt")),
    ))
    db.flush()
        
    telemetry_logger.info(json.dumps({
        "event": "interrogation_turn",
        "session_id": session_id,
        "suspect_id": suspect_id,
        "msg_analysis": {
            "intent": msg_analysis.intent.value,
            "novelty": msg_analysis.novelty.value,
            "sensitivity_hit": msg_analysis.sensitivity_hit.value,
            "primary_topic_id": msg_analysis.primary_topic_id
        },
        "state_transition": {
            "conversation_effect": state_transition.conversation_effect.value,
            "npc_shift": state_transition.npc_shift.value,
            "patience": suspect_state.get("patience", 0),
            "pressure": suspect_state.get("pressure", 0)
        },
        "evidence_inserted": evidence_id is not None,
        "evidence_effect": evidence_effect,
        "topics_touched": len(msg_analysis.detected_topic_ids),
        "revealed_secrets_count": len(revealed_secrets),
        "broken_claims_count": len(newly_broken_claims) if newly_broken_claims else 0
    }))

    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "newly_broken_claims": newly_broken_claims if newly_broken_claims else None,
        "evidence_effect": evidence_effect,
        "suspect_state": suspect_state,
        "message_analysis": msg_analysis if settings.DEBUG_TURN_TRACE else None,
        "state_transition": state_transition if settings.DEBUG_TURN_TRACE else None,
        "narrative_feedback": narrative_fb.model_dump() if narrative_fb else None,
        "debug_trace": debug_trace,
        # T1.4: Contexto conversacional na resposta
        "active_topic_id": conversation_context.active_topic_id,
        "context_inherited": conversation_context.context_inherited,
        "move_type": move_type.value,
        # Sprint 3 T2.3
        "mechanical_effect": mechanical_effect,
        "narrative_effect": narrative_effect,
    }
