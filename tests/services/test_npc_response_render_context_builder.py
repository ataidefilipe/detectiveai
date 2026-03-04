import pytest
from app.services.npc_response_render_context_builder import build_render_context
from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult, MessageIntent, ConversationEffect, NoveltyLevel, SensitivityLevel
from app.api.schemas.render_context import ResponseMode

@pytest.fixture
def base_analysis():
    return MessageAnalysisResult(
        intent=MessageIntent.unknown,
        detected_topic_ids=[],
        sensitive_topic_ids=[],
        sensitivity_hit=SensitivityLevel.low,
        novelty=NoveltyLevel.new
    )

@pytest.fixture
def base_transition():
    return StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )

def test_build_render_context_revealed_facts(base_analysis, base_transition):
    ctx = build_render_context(
        transition=base_transition,
        analysis=base_analysis,
        revealed_facts=["Secret 1"]
    )
    assert ctx.response_mode == ResponseMode.partial_admission

def test_build_render_context_out_of_context_evasive(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis,
        evidence_effect="out_of_context"
    )
    assert ctx.response_mode == ResponseMode.evasive

def test_build_render_context_out_of_context_deny(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.more_defensive,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis,
        evidence_effect="out_of_context"
    )
    assert ctx.response_mode == ResponseMode.deny

def test_build_render_context_pressured_with_knowledge(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.pressured,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis,
        allowed_knowledge=["Fact 1"]
    )
    assert ctx.response_mode == ResponseMode.partial_admission

def test_build_render_context_pressured_no_knowledge(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.pressured,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis,
        allowed_knowledge=[]
    )
    assert ctx.response_mode == ResponseMode.evasive

def test_build_render_context_defensive(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.more_defensive,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis
    )
    assert ctx.response_mode == ResponseMode.deny
    assert "alibi_contradiction" in ctx.forbidden_topics

def test_build_render_context_cooperative(base_analysis):
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.more_cooperative,
        state_deltas={},
        debug_reason_codes=[]
    )
    ctx = build_render_context(
        transition=transition,
        analysis=base_analysis
    )
    assert ctx.response_mode == ResponseMode.clarify
