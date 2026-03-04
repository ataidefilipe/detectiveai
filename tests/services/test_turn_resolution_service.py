import pytest
from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    ConversationEffect,
    NpcShift,
    NoveltyLevel
)
from app.services.turn_resolution_service import resolve_turn_state

def test_resolve_turn_state_pressure():
    analysis = MessageAnalysisResult(intent=MessageIntent.pressure)
    # Start at 70 pressure so the +15 from intent crosses the 80 threshold
    current_state = {"patience": 50.0, "pressure": 70.0, "stance": "neutral"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.conversation_effect == ConversationEffect.none
    assert transition.npc_shift == NpcShift.pressured
    assert "pressure" in transition.state_deltas
    assert transition.state_deltas["pressure"] > 0

def test_resolve_turn_state_calm():
    analysis = MessageAnalysisResult(intent=MessageIntent.calm)
    # Start pressured, with pressure 35, calm (-5) drops it to 30, which triggers cooperative
    current_state = {"patience": 50.0, "pressure": 35.0, "stance": "pressured"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.npc_shift == NpcShift.more_cooperative
    assert "rapport" in transition.state_deltas
    assert "pressure" in transition.state_deltas
    assert transition.state_deltas["rapport"] > 0
    assert transition.state_deltas["pressure"] < 0

def test_resolve_turn_state_neutral():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown)
    current_state = {"patience": 50.0, "pressure": 0.0, "stance": "neutral"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.conversation_effect == ConversationEffect.none
    assert transition.npc_shift == NpcShift.none
    assert transition.state_deltas == {}
    assert "mock_turn_resolution_mvp" in transition.debug_reason_codes

def test_resolve_turn_state_repetition_penalty():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown, novelty=NoveltyLevel.repeat)
    current_state = {"patience": 50.0, "pressure": 0.0, "stance": "neutral"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.state_deltas["patience"] == -15.0
    assert "penalized_for_repetition" in transition.debug_reason_codes

def test_resolve_turn_state_defensive_shift():
    analysis = MessageAnalysisResult(intent=MessageIntent.pressure, novelty=NoveltyLevel.repeat)
    # Start at 20 patience, repetition will drop it to 5 <= 10 threshold -> triggers defensive
    current_state = {"patience": 20.0, "pressure": 0.0, "stance": "neutral"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.npc_shift == NpcShift.more_defensive
    assert transition.state_deltas["stance"] == "defensive"

def test_resolve_turn_state_sensitive_topic():
    from app.api.schemas.chat import SensitivityLevel
    analysis = MessageAnalysisResult(
        intent=MessageIntent.unknown,
        sensitivity_hit=SensitivityLevel.high
    )
    current_state = {"patience": 50.0, "pressure": 0.0, "stance": "neutral"}
    transition = resolve_turn_state(analysis, current_state)
    
    assert transition.conversation_effect == ConversationEffect.sensitive_touch
    assert transition.state_deltas["patience"] == -10.0
    assert transition.state_deltas["pressure"] == 10.0
    assert "sensitive_topic_touched" in transition.debug_reason_codes

def test_resolve_turn_state_new_topic():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown)
    current_state = {"patience": 50.0, "pressure": 0.0, "stance": "neutral"}
    topic_state = {"status": "untouched", "times_touched": 0, "sensitive_heat": 0.0}
    
    transition = resolve_turn_state(analysis, current_state, topic_state)
    assert transition.conversation_effect == ConversationEffect.new_topic

def test_resolve_turn_state_topic_saturation():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown)
    current_state = {"patience": 50.0, "pressure": 0.0, "stance": "neutral"}
    topic_state = {"status": "active", "times_touched": 4, "sensitive_heat": 0.0}
    
    transition = resolve_turn_state(analysis, current_state, topic_state)
    assert transition.state_deltas["patience"] == -20.0
    assert "penalized_topic_saturation" in transition.debug_reason_codes

def test_resolve_turn_state_warm_topic_defensive():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown)
    current_state = {"patience": 50.0, "pressure": 70.0, "stance": "neutral"}
    topic_state = {"status": "active", "times_touched": 2, "sensitive_heat": 60.0}
    
    transition = resolve_turn_state(analysis, current_state, topic_state)
    # The pressure increases due to heat: 70 + 5 = 75. 
    # Not enough to reach 80.
    assert transition.state_deltas["pressure"] == 5.0
    assert transition.npc_shift == NpcShift.none
