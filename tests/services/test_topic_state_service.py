import pytest
from app.services.topic_state_service import get_topic_state, update_topic_hit
from app.infra.db_models import SessionSuspectTopicStateModel
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session_with_topic():
    db = TestingSessionLocal()
    topic = SessionSuspectTopicStateModel(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        status="untouched",
        times_touched=0,
        sensitive_heat=0.0
    )
    db.add(topic)
    db.commit()
    yield db
    db.query(SessionSuspectTopicStateModel).delete()
    db.commit()
    db.close()

def test_get_topic_state(db_session_with_topic):
    state = get_topic_state(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        db=db_session_with_topic
    )
    assert state["topic_id"] == "test_topic"
    assert state["status"] == "untouched"
    assert state["times_touched"] == 0
    assert state["sensitive_heat"] == 0.0

def test_update_topic_hit_basic(db_session_with_topic):
    state = update_topic_hit(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        db=db_session_with_topic
    )
    assert state["times_touched"] == 1
    assert state["status"] == "touched" # Default transition
    assert state["sensitive_heat"] == 0.0

def test_update_topic_hit_heat_and_status(db_session_with_topic):
    state = update_topic_hit(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        heat_delta=15.5,
        new_status="active",
        db=db_session_with_topic
    )
    assert state["times_touched"] == 1
    assert state["status"] == "active"
    assert state["sensitive_heat"] == 15.5

def test_update_topic_hit_heat_clamping(db_session_with_topic):
    update_topic_hit(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        heat_delta=150.0,
        db=db_session_with_topic
    )
    state = update_topic_hit(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        heat_delta=-200.0,
        db=db_session_with_topic
    )
    assert state["sensitive_heat"] == 0.0 # Clamped min 0.0
