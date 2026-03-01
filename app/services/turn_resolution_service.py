from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    StateTransitionResult,
    ConversationEffect,
    NpcShift,
    NoveltyLevel
)

def resolve_turn_state(
    analysis: MessageAnalysisResult, 
    current_state: dict
) -> StateTransitionResult:
    """
    Função MVP que resolve o impacto sistêmico do turno calculando deltas.
    
    Recebe a análise estruturada e o estado atual e cospe a transição de estado.
    Isso serve de ponte mecânica antes da IA verbalizar a resposta.
    """
    conversation_effect = ConversationEffect.none
    npc_shift = NpcShift.none
    deltas = {}
    reason_codes = ["mock_turn_resolution_mvp"]
    
    current_patience = float(current_state.get("patience", 50.0))
    current_pressure = float(current_state.get("pressure", 0.0))
    current_stance = current_state.get("stance", "neutral")
    
    # 1. Evaluate Message Analysis traits (Novelty)
    if analysis.novelty == NoveltyLevel.repeat:
        deltas["patience"] = -15.0
        reason_codes.append("penalized_for_repetition")

    # 2. Evaluate Intent heuristics for Deltas
    if analysis.intent == MessageIntent.pressure:
        deltas["pressure"] = 15.0
        reason_codes.append("intent_pressure_detected")
    elif analysis.intent == MessageIntent.calm:
        deltas["rapport"] = +10.0
        deltas["pressure"] = -5.0
        reason_codes.append("intent_calm_detected")

    # 3. Simulate future state to decide NpcShift & Stance change
    future_patience = current_patience + deltas.get("patience", 0.0)
    future_pressure = current_pressure + deltas.get("pressure", 0.0)
    
    if future_patience <= 10.0 and current_stance != "defensive":
        npc_shift = NpcShift.more_defensive
        deltas["stance"] = "defensive"
        reason_codes.append("shifted_defensive_due_to_patience")
        
    elif future_pressure >= 80.0 and current_stance != "pressured":
        npc_shift = NpcShift.pressured
        deltas["stance"] = "pressured"
        reason_codes.append("shifted_pressured")
    
    # Example backward transitions for cooperation
    elif future_patience >= 40.0 and future_pressure <= 30.0 and current_stance in ["defensive", "pressured"]:
        npc_shift = NpcShift.more_cooperative
        deltas["stance"] = "neutral"
        reason_codes.append("shifted_cooperative_due_to_deescalation")

    return StateTransitionResult(
        conversation_effect=conversation_effect,
        npc_shift=npc_shift,
        state_deltas=deltas,
        debug_reason_codes=reason_codes
    )
