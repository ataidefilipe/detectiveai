import pytest
from unittest.mock import mock_open
from app.services.scenario_loader import load_scenario_from_json
from app.core.exceptions import DomainError
from tests.conftest import TestingSessionLocal
import json

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()

def test_load_scenario_duplicate_suspect_id(db_session, monkeypatch):
    invalid_json = {
        "scenario_code": "test-dup-suspect",
        "title": "Dup Suspect",
        "description": "Teste",
        "culprit": "suspect1",
        "motives": [],
        "true_motive_key": None,
        "suspects": [
            {"id": "suspect1", "name": "Suspect 1"},
            {"id": "suspect1", "name": "Suspect 1 Duplicate"}
        ],
        "evidences": [{"id": "pista_1", "name": "Pista 1"}],
        "secrets": []
    }
    
    monkeypatch.setattr("builtins.open", mock_open(read_data=json.dumps(invalid_json)))
    
    with pytest.raises(DomainError, match="Duplicate suspect id found in scenario: 'suspect1'"):
        load_scenario_from_json("fake_path.json", db=db_session)

def test_load_scenario_duplicate_evidence_id(db_session, monkeypatch):
    invalid_json = {
        "scenario_code": "test-dup-evidence",
        "title": "Dup Evidence",
        "description": "Teste",
        "culprit": "suspect1",
        "motives": [],
        "true_motive_key": None,
        "suspects": [{"id": "suspect1", "name": "Suspect 1"}],
        "evidences": [
            {"id": "pista_1", "name": "Pista 1"},
            {"id": "pista_1", "name": "Pista 1 Duplicate"}
        ],
        "secrets": []
    }
    
    monkeypatch.setattr("builtins.open", mock_open(read_data=json.dumps(invalid_json)))
    
    with pytest.raises(DomainError, match="Duplicate evidence id found in scenario: 'pista_1'"):
        load_scenario_from_json("fake_path.json", db=db_session)
