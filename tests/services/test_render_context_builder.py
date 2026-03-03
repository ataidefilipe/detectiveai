import pytest
from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult, ConversationEffect, MessageIntent
from app.api.schemas.render_context import ResponseMode
from app.services.npc_response_render_context_builder import build_render_context

def test_build_render_context_revealed_facts():
    transition = StateTransitionResult(npc_shift=NpcShift.more_defensive)
    analysis = MessageAnalysisResult(intent=MessageIntent.ask)
    
    # Even if defensive, new facts force partial admission
    rc = build_render_context(
        transition=transition,
        analysis=analysis,
        revealed_facts=["Fato revelado via evidência"]
    )
    assert rc.response_mode == ResponseMode.partial_admission

def test_build_render_context_out_of_context():
    transition1 = StateTransitionResult(npc_shift=NpcShift.more_defensive)
    analysis = MessageAnalysisResult(intent=MessageIntent.ask)
    
    rc1 = build_render_context(
        transition=transition1,
        analysis=analysis,
        evidence_effect="out_of_context"
    )
    assert rc1.response_mode == ResponseMode.deny
    
    transition2 = StateTransitionResult(npc_shift=NpcShift.pressured)
    rc2 = build_render_context(
        transition=transition2,
        analysis=analysis,
        evidence_effect="out_of_context"
    )
    assert rc2.response_mode == ResponseMode.evasive

def test_build_render_context_pressured_with_knowledge():
    transition = StateTransitionResult(npc_shift=NpcShift.pressured)
    analysis = MessageAnalysisResult(intent=MessageIntent.pressure)
    
    # Pressured + Knowledge = partial admission
    rc_know = build_render_context(
        transition=transition,
        analysis=analysis,
        allowed_knowledge=["Conhecimento permitido"]
    )
    assert rc_know.response_mode == ResponseMode.partial_admission
    
    # Pressured + No Knowledge = evasive
    rc_noknow = build_render_context(
        transition=transition,
        analysis=analysis
    )
    assert rc_noknow.response_mode == ResponseMode.evasive

def test_build_render_context_defensive_no_content():
    transition = StateTransitionResult(npc_shift=NpcShift.more_defensive)
    analysis = MessageAnalysisResult(intent=MessageIntent.ask)
    
    rc = build_render_context(
        transition=transition,
        analysis=analysis
    )
    assert rc.response_mode == ResponseMode.deny

def test_build_render_context_cooperative():
    transition = StateTransitionResult(npc_shift=NpcShift.more_cooperative)
    analysis = MessageAnalysisResult(intent=MessageIntent.ask)
    
    rc = build_render_context(
        transition=transition,
        analysis=analysis
    )
    assert rc.response_mode == ResponseMode.clarify
