import pytest
from app.domain.schema_scenario import SpeechProfile, TopicAffinityProfile
from app.api.schemas.render_context import ResponseMode, SpeechDirective, NpcResponseRenderContext
from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult, MessageIntent
from app.services.npc_mode_policy_service import determine_speech_directive
from app.services.npc_response_render_context_builder import build_render_context
from app.services.prompt_builder import build_npc_prompt


def test_default_speech_profile():
    directive = determine_speech_directive(
        profile=None,
        pressure=0.0,
        patience=50.0,
        stance="neutral",
        response_mode=ResponseMode.neutral_answer
    )
    assert directive.min_sentences == 2
    assert directive.max_sentences == 3
    assert directive.target_max_words == 65
    assert "equilibrado" in directive.rhythm_hint


def test_high_stress_talkative_profile_marina():
    profile = SpeechProfile(base_verbosity=0.5, stress_verbosity_delta=0.5)
    directive = determine_speech_directive(
        profile=profile,
        pressure=85.0,
        patience=40.0,
        stance="pressured",
        response_mode=ResponseMode.claim_reaction
    )
    # Under high pressure (p=0.85), raw verbosity > 0.70
    assert directive.min_sentences == 3
    assert directive.max_sentences == 5
    assert directive.target_max_words == 95
    assert "ansiosa" in directive.rhythm_hint


def test_high_stress_laconic_profile_eduardo():
    profile = SpeechProfile(base_verbosity=0.3, stress_verbosity_delta=-0.5)
    directive = determine_speech_directive(
        profile=profile,
        pressure=80.0,
        patience=50.0,
        stance="pressured",
        response_mode=ResponseMode.guarded
    )
    # Under pressure, verbosity drops below 0.30
    assert directive.min_sentences == 1
    assert directive.max_sentences == 2
    assert directive.target_max_words == 35
    assert "seca" in directive.rhythm_hint or "lacônica" in directive.rhythm_hint


def test_special_mode_context_request():
    profile = SpeechProfile(base_verbosity=0.8, stress_verbosity_delta=0.2)
    directive = determine_speech_directive(
        profile=profile,
        pressure=50.0,
        patience=50.0,
        stance="neutral",
        response_mode=ResponseMode.context_request
    )
    # Context request should be exactly 1 short sentence
    assert directive.min_sentences == 1
    assert directive.max_sentences == 1
    assert directive.target_max_words == 25
    assert "especificidade" in directive.rhythm_hint


def test_special_mode_irritated_repeat():
    profile = SpeechProfile(base_verbosity=0.8, stress_verbosity_delta=0.2)
    directive = determine_speech_directive(
        profile=profile,
        pressure=20.0,
        patience=20.0,
        stance="neutral",
        response_mode=ResponseMode.irritated_repeat
    )
    # Irritated repeat cuts down words
    assert directive.min_sentences == 1
    assert directive.max_sentences == 2
    assert directive.target_max_words == 40
    assert "repetição" in directive.rhythm_hint


def test_build_render_context_modulates_speech():
    transition = StateTransitionResult(
        npc_shift=NpcShift.pressured,
        patience_delta=-5,
        pressure_delta=20
    )
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        primary_topic_id="relatorio",
        detected_topic_ids=["relatorio"]
    )
    
    class DummySuspect:
        claims = []
        profile = {
            "speech": {
                "base_verbosity": 0.5,
                "stress_verbosity_delta": 0.5
            }
        }
    
    rc = build_render_context(
        transition=transition,
        analysis=analysis,
        suspect=DummySuspect(),
        pressure=90.0,
        patience=30.0
    )
    
    assert rc.speech_directive is not None
    assert rc.speech_directive.min_sentences == 3
    assert rc.speech_directive.max_sentences == 5
    assert rc.speech_directive.target_max_words == 95


def test_prompt_builder_includes_speech_directive():
    rc = NpcResponseRenderContext(
        response_mode=ResponseMode.neutral_answer,
        speech_directive=SpeechDirective(
            min_sentences=1,
            max_sentences=2,
            target_max_words=35,
            rhythm_hint="fala extremamente seca e lacônica"
        )
    )
    npc_context = {
        "suspect": {
            "name": "Eduardo Farias",
            "personality": "arrogante"
        }
    }
    
    messages = build_npc_prompt(
        npc_context=npc_context,
        chat_history=[],
        render_context=rc
    )
    
    system_prompt = messages[0]["content"]
    assert "== EXTENSAO E RITMO ==" in system_prompt
    assert "prefira 1 a 2 frases" in system_prompt
    assert "35 palavras" in system_prompt
    assert "fala extremamente seca e lacônica" in system_prompt
    assert "Mais fala NAO autoriza mais fatos" in system_prompt
