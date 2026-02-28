import pytest
import os
import json
import tempfile
from sqlalchemy.orm import Session
from app.main import app
from tests.conftest import TestingSessionLocal
from app.services.scenario_loader import load_scenario_from_json
from app.infra.db_models import ScenarioModel, SuspectModel

def test_scenario_loader_rollback_on_invalid_culprit():
    db = TestingSessionLocal()
    try:
        # 1. Check initial state
        initial_scenarios = db.query(ScenarioModel).count()
        initial_suspects = db.query(SuspectModel).count()

        # 2. Create an invalid JSON (culprit does not exist in suspects list)
        invalid_data = {
            "title": "Invalid Story",
            "description": "Will crash half-way",
            "culprit": "Ghost",
            "suspects": [
                {"name": "Real Person"}
            ],
            "evidences": [],
            "secrets": []
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(invalid_data, tmp)
            tmp_path = tmp.name

        # 3. Attempt to load
        with pytest.raises(ValueError, match="not found among suspects"):
             load_scenario_from_json(tmp_path, db=db)

        # 4. Verify DB is perfectly clean
        final_scenarios = db.query(ScenarioModel).count()
        final_suspects = db.query(SuspectModel).count()

        assert final_scenarios == initial_scenarios, "Scenario table was polluted!"
        assert final_suspects == initial_suspects, "Suspect table was polluted!"

    finally:
        db.close()
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
