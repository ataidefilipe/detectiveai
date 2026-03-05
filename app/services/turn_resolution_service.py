from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    StateTransitionResult,
    ConversationEffect,
    NpcShift,
    NoveltyLevel,
    SensitivityLevel
)
from app.core.config import settings

def resolve_turn_state(
    analysis: MessageAnalysisResult, 
    current_state: dict,
    topic_state: dict = None
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
        deltas["patience"] = settings.PENALTY_FOR_REPETITION
        reason_codes.append("penalized_for_repetition")

    # 2. Evaluate Intent heuristics for Deltas
    if analysis.intent == MessageIntent.pressure:
        deltas["pressure"] = settings.INTENT_PRESSURE_GAIN
        reason_codes.append("intent_pressure_detected")
    elif analysis.intent == MessageIntent.calm:
        deltas["rapport"] = settings.INTENT_CALM_RAPPORT_GAIN
        deltas["pressure"] = settings.INTENT_CALM_PRESSURE_DROP
        reason_codes.append("intent_calm_detected")

    # 3. Evaluate Sensitive Topic Impact
    if analysis.sensitivity_hit == SensitivityLevel.high:
        deltas["pressure"] = deltas.get("pressure", 0.0) + settings.SENSITIVE_TOPIC_PRESSURE_GAIN
        deltas["patience"] = deltas.get("patience", 0.0) + settings.SENSITIVE_TOPIC_PATIENCE_DROP
        conversation_effect = ConversationEffect.sensitive_touch
        reason_codes.append("sensitive_topic_touched")
        
    # 3.5 Evaluate Topic State Heuristics (Task 6)
    if topic_state:
        times_touched = topic_state.get("times_touched", 0)
        status = topic_state.get("status", "untouched")
        sensitive_heat = topic_state.get("sensitive_heat", 0.0)
        
        if status == "untouched" and conversation_effect == ConversationEffect.none:
            conversation_effect = ConversationEffect.new_topic
            
        if times_touched > settings.TOPIC_SATURATION_TOUCH_COUNT:
            # Penalidade maior para spam de tópico saturado
            deltas["patience"] = deltas.get("patience", 0.0) + settings.TOPIC_SATURATION_PENALTY
            reason_codes.append("penalized_topic_saturation")
            
        if sensitive_heat > settings.TOPIC_HOT_HEAT_THRESHOLD:
            # Tópico muito quente aumenta a chance de defesa
            deltas["pressure"] = deltas.get("pressure", 0.0) + settings.TOPIC_HOT_PRESSURE_GAIN

    # 4. Simulate future state to decide NpcShift & Stance change
    future_patience = current_patience + deltas.get("patience", 0.0)
    future_pressure = current_pressure + deltas.get("pressure", 0.0)
    
    if future_patience <= settings.STANCE_DEFENSIVE_PATIENCE_THRESHOLD and current_stance != "defensive":
        npc_shift = NpcShift.more_defensive
        deltas["stance"] = "defensive"
        reason_codes.append("shifted_defensive_due_to_patience")
        
    elif future_pressure >= settings.STANCE_PRESSURED_PRESSURE_THRESHOLD and current_stance != "pressured":
        npc_shift = NpcShift.pressured
        deltas["stance"] = "pressured"
        reason_codes.append("shifted_pressured")
    
    # Example backward transitions for cooperation
    elif future_patience >= settings.STANCE_COOPERATIVE_PATIENCE_THRESHOLD and future_pressure <= settings.STANCE_COOPERATIVE_PRESSURE_THRESHOLD and current_stance in ["defensive", "pressured"]:
        npc_shift = NpcShift.more_cooperative
        deltas["stance"] = "neutral"
        reason_codes.append("shifted_cooperative_due_to_deescalation")

    return StateTransitionResult(
        conversation_effect=conversation_effect,
        npc_shift=npc_shift,
        state_deltas=deltas,
        debug_reason_codes=reason_codes
    )
