import pytest
from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    ConversationEffect,
    NpcShift
)
from app.services.turn_resolution_service import resolve_turn_state

def test_resolve_turn_state_pressure():
    analysis = MessageAnalysisResult(intent=MessageIntent.pressure)
    transition = resolve_turn_state(analysis)
    
    assert transition.conversation_effect == ConversationEffect.none
    assert transition.npc_shift == NpcShift.pressured
    assert "pressure" in transition.state_deltas
    assert transition.state_deltas["pressure"] > 0

def test_resolve_turn_state_calm():
    analysis = MessageAnalysisResult(intent=MessageIntent.calm)
    transition = resolve_turn_state(analysis)
    
    assert transition.npc_shift == NpcShift.more_cooperative
    assert "rapport" in transition.state_deltas
    assert "pressure" in transition.state_deltas
    assert transition.state_deltas["rapport"] > 0
    assert transition.state_deltas["pressure"] < 0

def test_resolve_turn_state_neutral():
    analysis = MessageAnalysisResult(intent=MessageIntent.unknown)
    transition = resolve_turn_state(analysis)
    
    assert transition.conversation_effect == ConversationEffect.none
    assert transition.npc_shift == NpcShift.none
    assert transition.state_deltas == {}
    assert "mock_turn_resolution_mvp" in transition.debug_reason_codes
