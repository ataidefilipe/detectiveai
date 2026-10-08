from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult, MessageIntent
from app.api.schemas.render_context import ResponseMode
from typing import Optional, List, Dict, Any

def determine_response_mode(
    transition: StateTransitionResult,
    analysis: MessageAnalysisResult,
    has_newly_broken_claims: bool = False,
    has_revealed_secrets: bool = False,
    has_new_knowledge: bool = False,
    evidence_effect: str = "none"
) -> ResponseMode:
    """
    Decide qual será a diretriz de atuação da LLM com as decisões já tomadas pelo motor mecânico.
    Regras MVP:
    * explore + baixa pressão -> neutral_answer
    * pressure sem prova -> guarded ou evasive
    * claim quebrado -> partial_admission ou contradiction_repair
    """

    # 1. Admissões ou reparos por quebra (Sprint 3 T5.2)
    if has_newly_broken_claims:
        return ResponseMode.claim_reaction
        
    if has_revealed_secrets:
        return ResponseMode.evidence_reaction

    if has_new_knowledge:
        if transition.npc_shift == NpcShift.more_defensive:
            return ResponseMode.contradiction_repair
        return ResponseMode.partial_admission

    # 1.5. Repetição e Falta de Especificidade
    from app.api.schemas.chat import NoveltyLevel, SpecificityLevel
    if analysis.novelty == NoveltyLevel.repeat:
        return ResponseMode.irritated_repeat
        
    if analysis.specificity == SpecificityLevel.low and not analysis.detected_topic_ids:
        return ResponseMode.context_request

    # 2. Deflexão sob pressão ou efeito adverso de evidência
    if evidence_effect == "out_of_context":
        if transition.npc_shift == NpcShift.more_defensive:
            return ResponseMode.deny
        return ResponseMode.evasive
        
    if transition.npc_shift == NpcShift.pressured:
        if evidence_effect == "reaction_only":
            return ResponseMode.pressured_deflection
        return ResponseMode.guarded

    if transition.npc_shift == NpcShift.more_defensive:
        if analysis.intent == MessageIntent.pressure:
            return ResponseMode.guarded
        return ResponseMode.deny

    # 3. Interações normais
    if analysis.intent == MessageIntent.pressure:
        return ResponseMode.guarded

    if transition.npc_shift == NpcShift.more_cooperative:
        return ResponseMode.clarify

    return ResponseMode.neutral_answer
