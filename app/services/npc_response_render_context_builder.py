from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode

def build_render_context(
    state_transition: StateTransitionResult,
    msg_analysis: MessageAnalysisResult,
    revealed_secrets: list[dict]
) -> NpcResponseRenderContext:
    """
    Constrói o NpcResponseRenderContext, decidindo a diretriz de atuação da LLM
    com as decisões já tomadas pelo motor mecânico do jogo (MVP).
    """

    # Default
    response_mode = ResponseMode.neutral_answer
    npc_stance = state_transition.npc_shift.value
    allowed_facts = [s["content"] for s in revealed_secrets]

    # Map state transitions to strict LLM directives
    if state_transition.npc_shift == NpcShift.more_defensive:
        response_mode = ResponseMode.deny
    elif state_transition.npc_shift == NpcShift.pressured:
        response_mode = ResponseMode.evasive
    elif state_transition.npc_shift == NpcShift.more_cooperative:
        response_mode = ResponseMode.clarify

    # No futuro (fase D), a Reveal Policy Service adicionará 'Knowledges' ao 'allowed_facts'
    
    return NpcResponseRenderContext(
        response_mode=response_mode,
        npc_stance=npc_stance,
        allowed_facts=allowed_facts,
        player_intent=msg_analysis.intent.value,
        tone_hint=None # Definido para testes no MVP
    )
