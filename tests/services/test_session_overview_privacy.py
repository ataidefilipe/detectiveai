import pytest
from unittest.mock import MagicMock
from app.services.session_service import get_session_overview
from app.infra.db_models import SessionModel, ScenarioModel, SuspectModel, SessionSuspectStateModel
from datetime import datetime

def test_get_session_overview_hides_internal_state():
    """
    SESS-002-B: Ensure GET /sessions/{id} does not reveal progress or is_closed.
    """
    db = MagicMock()
    
    # 1. Mock session
    session = MagicMock(spec=SessionModel)
    session.id = 1
    session.scenario_id = 10
    session.status = "in_progress"
    session.created_at = datetime(2023, 1, 1)
    db.query.return_value.filter.return_value.first.side_effect = [session]
    
    # 2. Mock scenario
    scenario = MagicMock(spec=ScenarioModel)
    scenario.id = 10
    scenario.title = "Test Case"
    scenario.description = "A test description"
    scenario.motive_options = ["Greed", "Revenge"]
    db.query.return_value.filter.return_value.first.side_effect = [session, scenario]
    
    # 3. Mock suspects
    suspect = MagicMock(spec=SuspectModel)
    suspect.id = 101
    suspect.name = "John Doe"
    db.query.return_value.filter.return_value.all.side_effect = [[suspect]]
    
    # 4. Mock suspect states
    state = MagicMock(spec=SessionSuspectStateModel)
    state.suspect_id = 101
    state.progress = 0.75
    state.is_closed = True
    db.query.return_value.filter.return_value.all.side_effect = [[suspect], [state]]
    
    # Execute
    result = get_session_overview(session_id=1, db=db)
    
    # Verify suspects summary
    suspects = result["suspects"]
    assert len(suspects) == 1
    s_summary = suspects[0]
    
    assert s_summary["suspect_id"] == 101
    assert s_summary["name"] == "John Doe"
    
    # CRITICAL: progress and is_closed MUST be absent
    assert "progress" not in s_summary
    assert "is_closed" not in s_summary
