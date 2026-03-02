import pytest
from unittest.mock import patch, MagicMock

from app.services.interrogation_turn_service import run_interrogation_turn
from app.api.schemas.chat import MessageAnalysisResult, StateTransitionResult

@pytest.fixture
def base_mocks():
    """Mocks the pipeline for debug trace tests."""
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
        
        m_analyze.return_value = MessageAnalysisResult(detected_topic_ids=[])
        m_resolve.return_value = StateTransitionResult()
        
        db_mock = MagicMock()
        mock_generic = MagicMock()
        mock_generic.scenario.topic_config = None
        mock_generic.patience = 50.0
        mock_generic.pressure = 0.0
        mock_generic.stance = "neutral"
        mock_generic.sensitive_heat = 0.0
        mock_generic.frequency_count = 0
        db_mock.query.return_value.filter.return_value.first.return_value = mock_generic
        
        yield {"db": db_mock}

@patch("app.services.interrogation_turn_service.settings")
def test_debug_trace_enabled(mock_settings, base_mocks):
    """Test debugging returns full turn states when env flag is true."""
    mock_settings.DEBUG_TURN_TRACE = True
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="hello", evidence_id=None, db=base_mocks["db"])
    
    assert result.get("debug_trace") is not None
    assert result["debug_trace"].message_analysis is not None
    assert result["debug_trace"].state_transition is not None

@patch("app.services.interrogation_turn_service.settings")
def test_debug_trace_disabled(mock_settings, base_mocks):
    """Test standard mode does not leak inner state logic."""
    mock_settings.DEBUG_TURN_TRACE = False
    result = run_interrogation_turn(session_id=1, suspect_id=1, text="hello", evidence_id=None, db=base_mocks["db"])
    
    assert result.get("debug_trace") is None
