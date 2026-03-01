import pytest
import os
import json
import tempfile
from app.services.scenario_loader import load_scenario_from_json
from app.infra.db_models import ScenarioModel
from tests.conftest import TestingSessionLocal

def test_scenario_loader_with_topics():
    db = TestingSessionLocal()
    tmp_path = None
    try:
        data = {
            "title": "Topic Case",
            "culprit": "Suspect A",
            "suspects": [{"name": "Suspect A"}],
            "evidences": [{"name": "Evidence A"}],
            "secrets": [],
            "topics": [
                {
                    "id": "murder_weapon",
                    "label": "The Murder Weapon",
                    "aliases": ["knife", "blade", "dagger"],
                    "is_sensitive": True,
                    "priority": 10
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        scenario = load_scenario_from_json(tmp_path, db=db)
        
        assert scenario.title == "Topic Case"
        assert hasattr(scenario, "topics")
        assert len(scenario.topics) == 1
        assert scenario.topics[0]["id"] == "murder_weapon"
        assert scenario.topics[0]["label"] == "The Murder Weapon"
        assert scenario.topics[0]["is_sensitive"] is True
        assert "knife" in scenario.topics[0]["aliases"]

    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_scenario_loader_with_knowledge_items():
    db = TestingSessionLocal()
    tmp_path = None
    try:
        data = {
            "title": "Knowledge Case",
            "culprit": "Witness",
            "suspects": [{
                "name": "Witness",
                "knowledge": [
                    {
                        "id": "k1",
                        "topic_id": "murder_weapon",
                        "kind": "observed",
                        "reliability": "high",
                        "content_layers": ["I saw a knife", "It was bloody"]
                    }
                ]
            }],
            "evidences": [{"name": "Knife"}],
            "secrets": []
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        scenario = load_scenario_from_json(tmp_path, db=db)
        suspect = scenario.suspects[0]
        
        assert hasattr(suspect, "knowledge_items")
        assert len(suspect.knowledge_items) == 1
        
        k_item = suspect.knowledge_items[0]
        assert k_item["id"] == "k1"
        assert k_item["topic_id"] == "murder_weapon"
        assert k_item["kind"] == "observed"
        assert k_item["reliability"] == "high"
        assert len(k_item["content_layers"]) == 2
        assert k_item["content_layers"][0] == "I saw a knife"

    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
