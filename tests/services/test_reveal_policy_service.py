import pytest
from app.services.reveal_policy_service import evaluate_reveal_layer

def test_evaluate_reveal_layer_untouched():
    knowledge_item = {"content_layers": ["fact 1", "fact 2"]}
    suspect_state = {"patience": 50.0}
    topic_state = {"status": "untouched", "times_touched": 0}
    
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 0

def test_evaluate_reveal_layer_level_1():
    knowledge_item = {"content_layers": ["fact 1", "fact 2"]}
    suspect_state = {"patience": 50.0}
    topic_state = {"status": "touched", "times_touched": 1}
    
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 1

def test_evaluate_reveal_layer_level_2_pressure():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3"]}
    suspect_state = {"patience": 50.0, "pressure": 60.0}
    topic_state = {"status": "active", "times_touched": 2}
    
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 2

def test_evaluate_reveal_layer_level_3_high_pressure():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3", "fact 4"]}
    suspect_state = {"patience": 10.0, "pressure": 90.0}
    topic_state = {"status": "active", "times_touched": 3}
    
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 3

def test_evaluate_reveal_layer_clamped():
    knowledge_item = {"content_layers": ["fact 1"]} # Max layer is 1
    suspect_state = {"patience": 10.0, "pressure": 90.0}
    topic_state = {"status": "active", "times_touched": 3} # Would trigger level 3
    
    # Needs to clamp at 1
    # Needs to clamp at 1
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 1

def test_evaluate_reveal_layer_low_patience_blocking():
    knowledge_item = {"content_layers": ["fact 1", "fact 2"]}
    suspect_state = {"patience": 10.0, "pressure": 0.0, "rapport": 0.0}
    topic_state = {"status": "touched", "times_touched": 1}
    
    # Patience is low (<=30), pressure and rapport are low, so allowed_layer remains 0
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 0

def test_evaluate_reveal_layer_pressure_only_unlock():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3"]}
    suspect_state = {"patience": 50.0, "pressure": 60.0, "rapport": 90.0} # Rapport does not matter anymore
    topic_state = {"status": "active", "times_touched": 2}
    
    # Pressure > 50 (from REVEAL_LAYER_2_PRESSURE_MIN) and times_touched > 1 unlocks layer 2
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 2

def test_evaluate_reveal_layer_lie_blocked():
    knowledge_item = {"content_layers": ["fact 1", "fact 2"], "kind": "lie"}
    suspect_state = {"patience": 50.0, "pressure": 50.0} # Pressure < 60
    topic_state = {"status": "touched", "times_touched": 1}
    
    # Lie blocked because pressure < 60
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 0

def test_evaluate_reveal_layer_lie_revealed():
    knowledge_item = {"content_layers": ["fact 1", "fact 2"], "kind": "lie"}
    suspect_state = {"patience": 50.0, "pressure": 65.0} # Pressure >= 60
    topic_state = {"status": "touched", "times_touched": 1}
    
    # Lie revealed because pressure >= 60
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 1

def test_evaluate_reveal_layer_rumor_clamped():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3", "fact 4"], "kind": "rumor"}
    suspect_state = {"patience": 50.0, "pressure": 70.0, "rapport": 70.0}
    topic_state = {"status": "active", "times_touched": 3}
    
    # Normally 3 layers for this state, but rumors clamp to 2
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 2

def test_evaluate_reveal_layer_rumor_extreme():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3", "fact 4"], "kind": "rumor"}
    suspect_state = {"patience": 50.0, "pressure": 85.0} # Extreme pressure
    topic_state = {"status": "active", "times_touched": 3}
    
    # Clamp overridden
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 3

def test_evaluate_reveal_layer_observed_boost():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3"], "kind": "observed", "reliability": "high"}
    suspect_state = {"patience": 50.0, "pressure": 45.0, "rapport": 0.0} 
    topic_state = {"status": "touched", "times_touched": 1}
    
    # Normally allowed_layer is 1. Since observed + high rel + pressure > 40, it bumps to 2
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 2


def test_get_allowed_knowledge_facts_uses_provided_suspect_state():
    from unittest.mock import MagicMock
    from app.services.reveal_policy_service import get_allowed_knowledge_facts
    from app.infra.db_models import SuspectModel

    mock_db = MagicMock()
    mock_suspect = MagicMock(spec=SuspectModel)
    mock_suspect.knowledge_items = [
        {
            "id": "k1",
            "topic_id": "topic_alpha",
            "content_layers": ["layer 1 fact"]
        }
    ]
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_suspect, # suspect query
        None # k_state query
    ]

    # If suspect_state is passed with patience=36 (even if post-turn would be 22), layer 1 is unlocked
    eval_state = {"patience": 36.0, "pressure": 10.0, "rapport": 0.0}

    # Mock get_topic_state
    from unittest.mock import patch
    with patch("app.services.reveal_policy_service.get_topic_state", return_value={"status": "touched", "times_touched": 1}):
        result = get_allowed_knowledge_facts(
            session_id="sess_1",
            suspect_id="susp_1",
            detected_topics=["topic_alpha"],
            db=mock_db,
            suspect_state=eval_state
        )

    assert "layer 1 fact" in result["new_knowledge_this_turn"]

