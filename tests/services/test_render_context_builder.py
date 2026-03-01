import pytest
from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    StateTransitionResult,
    ConversationEffect,
    NpcShift
)
from app.api.schemas.render_context import ResponseMode
from app.services.npc_response_render_context_builder import build_render_context


def test_build_render_context_evasive():
    state_trans = StateTransitionResult(npc_shift=NpcShift.pressured)
    msg_analysis = MessageAnalysisResult(intent=MessageIntent.pressure)
    
    context = build_render_context(
        state_transition=state_trans,
        msg_analysis=msg_analysis,
        revealed_secrets=[]
    )
    
    assert context.response_mode == ResponseMode.evasive
    assert context.npc_stance == NpcShift.pressured.value
    assert context.player_intent == MessageIntent.pressure.value
    assert context.allowed_facts == []

def test_build_render_context_deny():
    state_trans = StateTransitionResult(npc_shift=NpcShift.more_defensive)
    msg_analysis = MessageAnalysisResult(intent=MessageIntent.confront)
    
    context = build_render_context(
        state_transition=state_trans,
        msg_analysis=msg_analysis,
        revealed_secrets=[{"content": "A faca estava na mesa"}]
    )
    
    assert context.response_mode == ResponseMode.deny
    assert context.npc_stance == NpcShift.more_defensive.value
    assert context.allowed_facts == ["A faca estava na mesa"]

def test_build_render_context_clarify():
    state_trans = StateTransitionResult(npc_shift=NpcShift.more_cooperative)
    msg_analysis = MessageAnalysisResult(intent=MessageIntent.calm)
    
    context = build_render_context(
        state_transition=state_trans,
        msg_analysis=msg_analysis,
        revealed_secrets=[]
    )
    
    assert context.response_mode == ResponseMode.clarify
