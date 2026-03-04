import pytest
from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    SensitivityLevel,
    StateTransitionResult,
    ConversationEffect,
    NpcShift,
    TopicSignal
)
from app.services.turn_feedback_service import build_turn_feedback

def test_build_turn_feedback_vague():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=[],
        sensitivity_hit=SensitivityLevel.low
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="none")
    assert t_signal == TopicSignal.weak
    assert "pergunta muito vaga" in hints

def test_build_turn_feedback_out_of_context():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=["faca"],
        sensitivity_hit=SensitivityLevel.low
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="out_of_context")
    # Even if topic was detected, out of context dominates the hints 
    # although topic signal could be good because a topic was hit
    assert "evidência fora de contexto" in hints
    assert t_signal == TopicSignal.good

def test_build_turn_feedback_sensitivity_strong():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=["crime"],
        sensitivity_hit=SensitivityLevel.high
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.sensitive_touch,
        npc_shift=NpcShift.pressured, # good shift
        state_deltas={},
        debug_reason_codes=[]
    )
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="none")
    assert t_signal == TopicSignal.strong
    assert "tema sensível tocado adequadamente" in hints

def test_build_turn_feedback_sensitivity_weak():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=["crime"],
        sensitivity_hit=SensitivityLevel.high
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.sensitive_touch,
        npc_shift=NpcShift.more_defensive, # bad shift
        state_deltas={},
        debug_reason_codes=[]
    )
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="none")
    assert t_signal == TopicSignal.weak
    assert "suspeito recuou ao tocar em tema sensível" in hints

def test_build_turn_feedback_topic_saturation():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=["crime"],
        sensitivity_hit=SensitivityLevel.low
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )
    topic_state = {"times_touched": 3}
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="none", topic_state=topic_state)
    assert t_signal == TopicSignal.weak
    assert "tópico já explorado" in hints
