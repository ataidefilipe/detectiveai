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
        times_touched=0
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

def test_update_topic_hit_basic(db_session_with_topic):
    state = update_topic_hit(
        session_id=999,
        suspect_id=888,
        topic_id="test_topic",
        db=db_session_with_topic
    )
    assert state["times_touched"] == 1
    assert state["status"] == "touched" # Default transition

def test_update_topic_hit_saturation(db_session_with_topic):
    from app.core.config import settings
    # Hit until saturation (threshold is 3, so hit 4 is saturation)
    for _ in range(settings.TOPIC_SATURATION_TOUCH_COUNT + 1):
        state = update_topic_hit(
            session_id=999,
            suspect_id=888,
            topic_id="test_topic",
            db=db_session_with_topic
        )
    
    assert state["times_touched"] == settings.TOPIC_SATURATION_TOUCH_COUNT + 1
    assert state["status"] == "saturated"
