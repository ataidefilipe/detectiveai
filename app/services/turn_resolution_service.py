from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    StateTransitionResult,
    ConversationEffect,
    NpcShift
)

def resolve_turn_state(analysis: MessageAnalysisResult) -> StateTransitionResult:
    """
    Função MVP que resolve o impacto sistêmico do turno.
    No MVP, a resolução é simples e heursítica com base na `MessageAnalysisResult`.
    
    Recebe a análise estruturada da mensagem e cospe a transição de estado.
    Isso serve de ponte mecânica antes da IA verbalizar a resposta.
    """
    
    conversation_effect = ConversationEffect.none
    npc_shift = NpcShift.none
    deltas = {}
    reason_codes = ["mock_turn_resolution_mvp"]
    
    # 1. Resolver NpcShift baseado na Intent (Mock MVP)
    if analysis.intent == MessageIntent.pressure:
        npc_shift = NpcShift.pressured
        deltas["pressure"] = +10
    elif analysis.intent == MessageIntent.calm:
        npc_shift = NpcShift.more_cooperative
        deltas["rapport"] = +10
        deltas["pressure"] = -5
    
    # Em tarefas futuras (Epic C e B), a resolução avaliará:
    # - repetition_score
    # - last_topic_id
    # - sensitivity
    # Por ora, retorna a estrutura básica instanciada

    return StateTransitionResult(
        conversation_effect=conversation_effect,
        npc_shift=npc_shift,
        state_deltas=deltas,
        debug_reason_codes=reason_codes
    )
