import os
from unittest.mock import patch, mock_open
import pytest
from app.services.scenario_loader import load_scenario_from_json
from app.infra.db_models import ScenarioModel
from app.core.exceptions import DomainError
from tests.conftest import TestingSessionLocal
import json

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()

def test_load_scenario_valid_motive(db_session, monkeypatch):
    valid_json = {
        "scenario_code": "test-valid",
        "title": "Cenário Válido Motivação",
        "description": "Teste",
        "culprit": "Fulano",
        "motives": [
            {"key": "revenge", "label": "Vingança"},
            {"key": "money", "label": "Dinheiro"}
        ],
        "true_motive_key": "money",
        "suspects": [
            {"name": "Fulano", "backstory": "Test"}
        ],
        "evidences": [
            {"name": "Pista 1", "is_mandatory": True}
        ],
        "secrets": [
            {"suspect": "Fulano", "evidence": "Pista 1", "content": "Segredo", "is_core": True}
        ]
    }
    
    # Mock json load
    monkeypatch.setattr("builtins.open", mock_open(read_data=json.dumps(valid_json)))
    
    scenario = load_scenario_from_json("fake_path.json", db=db_session)
    
    assert scenario is not None
    assert scenario.title == "Cenário Válido Motivação"
    assert scenario.true_motive_key == "money"
    assert len(scenario.motive_options) == 2
    assert scenario.motive_options[1]["key"] == "money"

def test_load_scenario_invalid_motive_key(db_session, monkeypatch):
    invalid_json = {
        "scenario_code": "test-invalid",
        "title": "Cenário Inválido Motivação",
        "description": "Teste",
        "culprit": "Fulano",
        "motives": [
            {"key": "revenge", "label": "Vingança"}
        ],
        "true_motive_key": "wrong_motive",
        "suspects": [{"name": "Fulano"}],
        "evidences": [{"name": "Pista 1"}],
        "secrets": [{"suspect": "Fulano", "evidence": "Pista 1", "content": "Seg", "is_core": True}]
    }
    
    monkeypatch.setattr("builtins.open", mock_open(read_data=json.dumps(invalid_json)))
    
    with pytest.raises(DomainError, match="true_motive_key 'wrong_motive' is not in motives list"):
        load_scenario_from_json("fake_path.json", db=db_session)
