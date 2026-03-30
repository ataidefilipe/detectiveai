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

    # 1. Admissões ou reparos por quebra
    if has_newly_broken_claims or has_revealed_secrets or has_new_knowledge:
        # Se foi pressionado a admitir ou quebrado com evidência, contradiction_repair ou partial_admission
        if transition.npc_shift == NpcShift.more_defensive:
            return ResponseMode.contradiction_repair
        return ResponseMode.partial_admission

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
