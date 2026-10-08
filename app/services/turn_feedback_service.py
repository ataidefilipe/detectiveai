from typing import Tuple, List, Optional, Dict, Any

from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
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
    topic_state: Optional[Dict[str, Any]] = None,
    newly_broken_claims: Optional[List[str]] = None,
    revealed_secrets: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[TopicSignal, List[str]]:
    """
    Consolidates the rules for generating TopicSignal and feedback_hints for the UI.
    Extracts the logic previously embedded in interrogation_turn_service.
    """
    hints = []
    t_signal = TopicSignal.none

    has_breakthrough = bool(newly_broken_claims or revealed_secrets)

    # 1. Conquistas mecânicas (quebra de claim ou segredo) têm precedência absoluta
    if has_breakthrough:
        t_signal = TopicSignal.strong
        if newly_broken_claims:
            hints.append("contradição desfeita")
        if revealed_secrets:
            hints.append("segredo revelado")
        return t_signal, hints

    # 2. Evidence context takes precedence in hints
    if evidence_effect == "out_of_context":
        hints.append("evidência fora de contexto")
        if analysis.sensitivity_hit.value in ["high", "medium"]:
            hints.append("tema promissor, mas evidência não encaixou")

    # 3. Sensitivity handling
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
        # 4. Normal topic detection
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

    # 5. Vague queries (apenas quando é pergunta aberta e não há tópicos nem evidências)
    # Acusações, pressões, acalmar ou confrontos NÃO são perguntas vagas!
    if not analysis.detected_topic_ids and evidence_effect == "none":
        if "evidência fora de contexto" not in hints:
            is_question = getattr(analysis, "intent", None) in (MessageIntent.ask, None)
            if is_question:
                hints.append("pergunta muito vaga")
                t_signal = TopicSignal.weak

    return t_signal, hints


def build_narrative_feedback(
    npc_shift: str,
    topic_signal: TopicSignal,
    evidence_effect: str,
    hints: List[str],
    newly_broken_claims: Optional[List[str]] = None,
    revealed_secrets: Optional[List[Dict[str, Any]]] = None,
    recent_guidances: Optional[List[str]] = None,
) -> NarrativeFeedback:
    """
    Translates internal system signals into narrative-focused feedback (diegetic)
    for the frontend, so the player receives qualitative hints rather than technical ones.
    Includes anti-spam cooldown and suppression on breakthroughs.
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
        
    # Se houve conquista mecânica (quebra de claim ou segredo revelado), suprime qualquer dica negativa!
    if newly_broken_claims or revealed_secrets:
        return NarrativeFeedback(
            suspect_reaction=reaction if reaction != SuspectReaction.neutro else SuspectReaction.pressionado,
            topic_read=TopicRead.sensivel,
            guidance=None
        )

    recent_guidances = recent_guidances or []
    guidance = None

    if evidence_effect == "out_of_context":
        if "tema promissor, mas evidência não encaixou" in hints:
            cand = "A direção é boa, mas essa ligação ainda não faz sentido para o suspeito."
        else:
            cand = "A conexão com o assunto ainda não ficou clara."
        guidance = cand if cand not in recent_guidances else None
    elif evidence_effect == "reaction_only":
        cand = "O suspeito sentiu o golpe, mas a evidência não provou nada por si só."
        guidance = cand if cand not in recent_guidances else None
    elif "pergunta muito vaga" in hints:
        cand = "A pergunta foi muito aberta. Tente especificar um horário, pessoa, lugar ou evidência."
        guidance = cand if cand not in recent_guidances else None
    elif "tópico já explorado" in hints:
        cand = "O assunto parece esgotado. O suspeito está ficando irritado com a repetição."
        guidance = cand if cand not in recent_guidances else None
        
    if guidance is None and topic_signal == TopicSignal.none:
        # Apenas emite 'não reagiu a nada' se realmente não houve efeito de evidência nem mudança de postura
        if evidence_effect in ("none", "") and npc_shift in ("none", ""):
            cand = "O suspeito não reagiu a nada de específico nessa troca."
            guidance = cand if cand not in recent_guidances else None
        
    return NarrativeFeedback(
        suspect_reaction=reaction,
        topic_read=t_read,
        guidance=guidance
    )
