import pytest
from unittest.mock import MagicMock

from app.services.session_service import calculate_suspect_progress
from app.infra.db_models import SecretModel, SessionSuspectStateModel
from app.core.exceptions import NotFoundError

def build_secret(sid, is_core):
    s = MagicMock(spec=SecretModel)
    s.id = sid
    s.is_core = is_core
    return s

def test_calculate_progress_with_core_secrets():
    db = MagicMock()
    
    # Mock suspect state
    state = MagicMock(spec=SessionSuspectStateModel)
    state.revealed_secret_ids = [10]
    db.query.return_value.filter.return_value.first.return_value = state
    
    # Mock secrets: 2 core, 1 regular
    db.query.return_value.filter.return_value.all.return_value = [
        build_secret(10, True),
        build_secret(11, True),
        build_secret(12, False)
    ]
    
    progress = calculate_suspect_progress(session_id=1, suspect_id=1, db=db)
    
    # Expected: 1 revealed core / 2 total core = 0.5
    assert progress == 0.5

def test_calculate_progress_with_only_regular_secrets():
    db = MagicMock()
    
    state = MagicMock(spec=SessionSuspectStateModel)
    state.revealed_secret_ids = [20, 21]
    db.query.return_value.filter.return_value.first.return_value = state
    
    # Mock secrets: 0 core, 4 regular
    db.query.return_value.filter.return_value.all.return_value = [
        build_secret(20, False),
        build_secret(21, False),
        build_secret(22, False),
        build_secret(23, False)
    ]
    
    progress = calculate_suspect_progress(session_id=1, suspect_id=1, db=db)
    
    # Expected: 2 revealed regular / 4 total regular = 0.5
    assert progress == 0.5

def test_calculate_progress_with_no_secrets():
    db = MagicMock()
    
    state = MagicMock(spec=SessionSuspectStateModel)
    state.revealed_secret_ids = []
    db.query.return_value.filter.return_value.first.return_value = state
    
    # Mock secrets: Empty
    db.query.return_value.filter.return_value.all.return_value = []
    
    progress = calculate_suspect_progress(session_id=1, suspect_id=1, db=db)
    
    # Expected: 0 secrets means 100% progress
    assert progress == 1.0

def test_calculate_progress_suspect_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(NotFoundError, match="does not belong to session"):
        calculate_suspect_progress(session_id=99, suspect_id=99, db=db)
