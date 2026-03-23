from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    SensitivityLevel,
    StateTransitionResult,
    ConversationEffect,
    NpcShift,
    TopicSignal,
    NarrativeFeedback,
    SuspectReaction,
    TopicRead
)
from app.services.turn_feedback_service import build_turn_feedback, build_narrative_feedback

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
    # Even if topic was detected, out_of_context dominates the hints 
    # although topic signal could be good because a topic was hit
    assert "evidência fora de contexto" in hints
    assert "tema promissor, mas evidência não encaixou" not in hints
    assert t_signal == TopicSignal.good

def test_build_turn_feedback_out_of_context_sensitive():
    analysis = MessageAnalysisResult(
        intent=MessageIntent.ask,
        detected_topic_ids=["faca"],
        sensitivity_hit=SensitivityLevel.high
    )
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.none,
        state_deltas={},
        debug_reason_codes=[]
    )
    
    t_signal, hints = build_turn_feedback(analysis, transition, evidence_effect="out_of_context")
    assert "evidência fora de contexto" in hints
    assert "tema promissor, mas evidência não encaixou" in hints
    assert t_signal == TopicSignal.strong

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

def test_build_narrative_feedback_defensive_weak():
    narrative_fb = build_narrative_feedback(
        npc_shift="more_defensive",
        topic_signal=TopicSignal.weak,
        evidence_effect="none",
        hints=[]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.defensivo
    assert narrative_fb.topic_read == TopicRead.fraco
    assert narrative_fb.guidance is None

def test_build_narrative_feedback_pressured_strong():
    narrative_fb = build_narrative_feedback(
        npc_shift="pressured",
        topic_signal=TopicSignal.strong,
        evidence_effect="none",
        hints=[]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.pressionado
    assert narrative_fb.topic_read == TopicRead.sensivel
    assert narrative_fb.guidance is None

def test_build_narrative_feedback_out_of_context():
    narrative_fb = build_narrative_feedback(
        npc_shift="none",
        topic_signal=TopicSignal.good,
        evidence_effect="out_of_context",
        hints=["evidência fora de contexto"]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.neutro
    assert narrative_fb.topic_read == TopicRead.promissor
    assert narrative_fb.guidance == "A conexão com o assunto ainda não ficou clara."

def test_build_narrative_feedback_out_of_context_promissor():
    narrative_fb = build_narrative_feedback(
        npc_shift="none",
        topic_signal=TopicSignal.strong,
        evidence_effect="out_of_context",
        hints=["evidência fora de contexto", "tema promissor, mas evidência não encaixou"]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.neutro
    assert narrative_fb.topic_read == TopicRead.sensivel
    assert narrative_fb.guidance == "A direção é boa, mas essa ligação ainda não faz sentido para o suspeito."

def test_build_narrative_feedback_vague_question():
    narrative_fb = build_narrative_feedback(
        npc_shift="none",
        topic_signal=TopicSignal.weak,
        evidence_effect="none",
        hints=["pergunta muito vaga"]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.neutro
    assert narrative_fb.topic_read == TopicRead.fraco
    assert narrative_fb.guidance == "A pergunta foi muito aberta e não obteve um foco claro."

def test_build_narrative_feedback_generic_guidance():
    narrative_fb = build_narrative_feedback(
        npc_shift="none",
        topic_signal=TopicSignal.none,
        evidence_effect="none",
        hints=[]
    )
    assert narrative_fb.suspect_reaction == SuspectReaction.neutro
    assert narrative_fb.topic_read == TopicRead.nenhum
    assert narrative_fb.guidance == "O suspeito não reagiu a nada de específico nessa troca."
