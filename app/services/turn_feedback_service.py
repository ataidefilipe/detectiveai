from typing import Tuple, List, Optional, Dict, Any

from app.api.schemas.chat import (
    MessageAnalysisResult,
    StateTransitionResult,
    TopicSignal,
    NarrativeFeedback,
    SuspectReaction,
    TopicRead
)

def build_turn_feedback(
    analysis: MessageAnalysisResult,
    transition: StateTransitionResult,
    evidence_effect: str,
    topic_state: Optional[Dict[str, Any]] = None
) -> Tuple[TopicSignal, List[str]]:
    """
    Consolidates the rules for generating TopicSignal and feedback_hints for the UI.
    Extracts the logic previously embedded in interrogation_turn_service.
    """
    hints = []
    t_signal = TopicSignal.none

    # 1. Evidence context takes precedence in hints
    if evidence_effect == "out_of_context":
        hints.append("evidência fora de contexto")
        if analysis.sensitivity_hit.value in ["high", "medium"]:
            hints.append("tema promissor, mas evidência não encaixou")

    # 2. Sensitivity handling
    if analysis.sensitivity_hit.value in ["high", "medium"]:
        if transition.npc_shift.value in ["more_cooperative", "pressured"]:
            hints.append("tema sensível tocado adequadamente")
            t_signal = TopicSignal.strong
        elif transition.npc_shift.value == "more_defensive":
            hints.append("suspeito recuou ao tocar em tema sensível")
            t_signal = TopicSignal.weak
        elif evidence_effect == "out_of_context":
            # If out of context but hit sensitive topic, we ensure strong signal
            t_signal = TopicSignal.strong
    else:
        # 3. Normal topic detection
        if analysis.detected_topic_ids:
            t_signal = TopicSignal.good
            
            # Use state transition effect or topic state repeat
            is_repeat = transition.conversation_effect.value == "repeat"
            if topic_state and topic_state.get("times_touched", 0) > 2:
                is_repeat = True
                
            if is_repeat:
                if "tópico já explorado" not in hints:
                    hints.append("tópico já explorado")
                t_signal = TopicSignal.weak

    # 4. Vague queries (no topic and no evidence)
    if not analysis.detected_topic_ids and evidence_effect == "none":
        # Only add vague hint if not already out of context
        if "evidência fora de contexto" not in hints:
            hints.append("pergunta muito vaga")
        t_signal = TopicSignal.weak

    return t_signal, hints


def build_narrative_feedback(
    npc_shift: str,
    topic_signal: TopicSignal,
    evidence_effect: str,
    hints: List[str]
) -> NarrativeFeedback:
    """
    Translates internal system signals into narrative-focused feedback (diegetic)
    for the frontend, so the player receives qualitative hints rather than technical ones.
    """
    reaction = SuspectReaction.neutro
    if npc_shift == "more_defensive":
        reaction = SuspectReaction.defensivo
    elif npc_shift == "pressured":
        reaction = SuspectReaction.pressionado
    elif npc_shift == "more_cooperative":
        reaction = SuspectReaction.cooperativo
    elif npc_shift == "irritated":
        reaction = SuspectReaction.irritado
        
    t_read = TopicRead.nenhum
    if topic_signal == TopicSignal.strong:
        t_read = TopicRead.sensivel
    elif topic_signal == TopicSignal.good:
        t_read = TopicRead.promissor
    elif topic_signal == TopicSignal.weak:
        t_read = TopicRead.fraco
        
    guidance = None
    if evidence_effect == "out_of_context":
        if "tema promissor, mas evidência não encaixou" in hints:
            guidance = "A direção é boa, mas essa ligação ainda não faz sentido para o suspeito."
        else:
            guidance = "A conexão com o assunto ainda não ficou clara."
    elif evidence_effect == "reaction_only":
        guidance = "O suspeito sentiu o golpe, mas a evidência não provou nada por si só."
    elif "pergunta muito vaga" in hints:
        guidance = "A pergunta foi muito aberta e não obteve um foco claro."
    elif "tópico já explorado" in hints:
        guidance = "Parece que vocês estão andando em círculos sobre esse assunto."
        
    return NarrativeFeedback(
        suspect_reaction=reaction,
        topic_read=t_read,
        guidance=guidance
    )
