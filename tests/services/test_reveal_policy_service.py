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
    assert evaluate_reveal_layer(knowledge_item, suspect_state, topic_state) == 1
