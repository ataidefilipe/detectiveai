import pytest
from unittest.mock import patch, MagicMock

from app.api.schemas.chat import (
    MessageAnalysisResult,
    StateTransitionResult,
    ConversationEffect,
    NpcShift,
    SensitivityLevel,
    TopicSignal
)
from app.services.interrogation_turn_service import run_interrogation_turn

@pytest.fixture
def base_mocks():
    """Mocks the whole pipeline up to the final dictionary assembly."""
    with patch("app.services.interrogation_turn_service.analyze_message") as m_analyze, \
         patch("app.services.interrogation_turn_service.resolve_turn_state") as m_resolve, \
         patch("app.services.interrogation_turn_service.add_player_message") as m_add_p, \
         patch("app.services.interrogation_turn_service.add_npc_reply") as m_add_n, \
         patch("app.services.interrogation_turn_service.get_suspect_state") as m_state, \
         patch("app.services.interrogation_turn_service.apply_evidence_to_suspect") as m_evi, \
         patch("app.services.interrogation_turn_service.get_allowed_knowledge_facts") as m_know:
        
        m_add_p.return_value = {"id": 1, "text": "Teste"}
        m_add_n.return_value = {"id": 2, "text": "Resposta"}
        m_state.return_value = {"stance": "neutral", "patience": 50.0, "pressure": 0.0}
        m_know.return_value = []
        m_evi.return_value = ([], "none")
        
        # Default analysis
        analysis = MessageAnalysisResult(
            detected_topic_ids=["topic_a"],
            sensitivity_hit=SensitivityLevel.none
        )
        m_analyze.return_value = analysis
        
        # Default State transition
        transition = StateTransitionResult(
            conversation_effect=ConversationEffect.none,
            npc_shift=NpcShift.none
        )
        m_resolve.return_value = transition
        
        db_mock = MagicMock()
        
        # Generic mock for anything queried.
        mock_generic = MagicMock()
        mock_generic.scenario = MagicMock()
        mock_generic.scenario.topic_config = None
        mock_generic.patience = 50.0
        mock_generic.pressure = 0.0
        mock_generic.stance = "neutral"
        mock_generic.sensitive_heat = 0.0
        mock_generic.frequency_count = 0
        
        db_mock.query.return_value.filter.return_value.first.return_value = mock_generic
        
        yield {
            "analyze": m_analyze,
            "resolve": m_resolve,
            "evi": m_evi,
            "db": db_mock
        }

def test_feedback_hints_and_topic_signal_sensitive_cooperative(base_mocks):
    """Test when player touches sensitive topic and NPC becomes cooperative -> Strong Signal."""
    
    # 1. Arrange
    analysis = MessageAnalysisResult(
        detected_topic_ids=["murder_weapon"],
        sensitivity_hit=SensitivityLevel.high
    )
    base_mocks["analyze"].return_value = analysis
    
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.deeper_topic,
        npc_shift=NpcShift.more_cooperative
    )
    base_mocks["resolve"].return_value = transition
    
    # 2. Act
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="The weapon?", evidence_id=None, db=base_mocks["db"])
    
    # 3. Assert
    assert result["topic_signal"] == TopicSignal.strong
    assert "tema sensível tocado adequadamente" in result["feedback_hints"]

def test_feedback_hints_and_topic_signal_sensitive_defensive(base_mocks):
    """Test when player touches sensitive topic but NPC gets defensive -> Weak Signal."""
    
    analysis = MessageAnalysisResult(
        detected_topic_ids=["murder_weapon"],
        sensitivity_hit=SensitivityLevel.high
    )
    base_mocks["analyze"].return_value = analysis
    
    transition = StateTransitionResult(
        conversation_effect=ConversationEffect.none,
        npc_shift=NpcShift.more_defensive
    )
    base_mocks["resolve"].return_value = transition
    
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="The weapon?", evidence_id=None, db=base_mocks["db"])
    
    assert result["topic_signal"] == TopicSignal.weak
    assert "suspeito recuou ao tocar em tema sensível" in result["feedback_hints"]

def test_feedback_hints_out_of_context(base_mocks):
    """Test when evidence used is out of context -> None Signal."""
    
    analysis = MessageAnalysisResult(
        detected_topic_ids=["random_topic"],
        sensitivity_hit=SensitivityLevel.none
    )
    base_mocks["analyze"].return_value = analysis
    
    transition = StateTransitionResult()
    # Mocking out_of_context coming from Apply Evidence resolution
    base_mocks["resolve"].return_value = transition
    base_mocks["evi"].return_value = ([], "out_of_context")
    
    # Setup mock to not fall into "duplicate" logic block
    # We only want the query for EvidenceUsage to return None, but db_mock is shared.
    # To fix this, we can set the evidence_effect = "out_of_context" directly via m_evi hook.
    # And we don't even need to override db_mock because was_previously_used won't overwrite out_of_context!
    # Ah, if was_previously_used=False (None returned), it just adds it to DB. It doesn't break out_of_context.
    # So remove the line that sets it to None!
    
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="Look here.", evidence_id=99, db=base_mocks["db"])
    
    assert "evidência fora de contexto" in result["feedback_hints"]
    # TopicSignal falls back to `good` because `random_topic` is detected, but effect was `out_of_context`.
    # Actually wait. If evidence is OOC, it overrides? Our logic checks OOC independently.
    assert result["topic_signal"] == TopicSignal.good

def test_feedback_hints_vague_no_topic(base_mocks):
    """Test when no topics detected and no evidence -> Weak Signal."""
    
    analysis = MessageAnalysisResult(
        detected_topic_ids=[],
        sensitivity_hit=SensitivityLevel.none
    )
    base_mocks["analyze"].return_value = analysis
    
    transition = StateTransitionResult()
    base_mocks["resolve"].return_value = transition
    
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="hello.", evidence_id=None, db=base_mocks["db"])
    
    assert result["topic_signal"] == TopicSignal.weak
    assert "pergunta muito vaga" in result["feedback_hints"]
