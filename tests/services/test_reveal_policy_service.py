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

def test_evaluate_reveal_layer_rapport_unlock():
    knowledge_item = {"content_layers": ["fact 1", "fact 2", "fact 3"]}
    suspect_state = {"patience": 50.0, "pressure": 0.0, "rapport": 60.0}
    topic_state = {"status": "active", "times_touched": 2}
    
    # Rapport > 50 and times_touched > 1 unlocks layer 2
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
