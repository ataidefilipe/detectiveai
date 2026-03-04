from typing import Tuple, List, Optional, Dict, Any

from app.api.schemas.chat import (
    MessageAnalysisResult,
    StateTransitionResult,
    TopicSignal
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

    # 2. Sensitivity handling
    if analysis.sensitivity_hit.value in ["high", "medium"]:
        if transition.npc_shift.value in ["more_cooperative", "pressured"]:
            hints.append("tema sensível tocado adequadamente")
            t_signal = TopicSignal.strong
        elif transition.npc_shift.value == "more_defensive":
            hints.append("suspeito recuou ao tocar em tema sensível")
            t_signal = TopicSignal.weak
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
