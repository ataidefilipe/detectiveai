import os
import pytest
from app.services.scenario_loader import load_scenario_from_json
from app.services.session_service import create_session, get_session_overview
from tests.conftest import TestingSessionLocal


def test_load_english_reviewed_scenario():
    db = TestingSessionLocal()
    scenario_path = os.path.join(
        os.path.dirname(__file__),
        "../scenarios/detective_scenario_piloto_02_reviewed_en.json"
    )
    assert os.path.exists(scenario_path), f"File not found: {scenario_path}"

    try:
        scenario = load_scenario_from_json(scenario_path, db=db)

        # Scenario metadata
        assert scenario.scenario_code == "piloto-03"
        assert scenario.title == "The Locked Office Case 01"
        assert scenario.true_motive_key == "financial_gain"
        assert scenario.required_broken_claim_ids == ["claim_marina_alibi_01"]

        # Suspects & Roles
        assert len(scenario.suspects) == 4
        suspect_map = {s.suspect_code: s for s in scenario.suspects}
        assert "marina_souza" in suspect_map
        assert "rogerio_lima" in suspect_map
        assert "clara_martins" in suspect_map
        assert "eduardo_farias" in suspect_map

        assert suspect_map["marina_souza"].role_title == "Financial Assistant"
        assert suspect_map["rogerio_lima"].role_title == "Security Guard"
        assert suspect_map["clara_martins"].role_title == "IT Intern"
        assert suspect_map["eduardo_farias"].role_title == "Commercial Manager"

        # Evidences
        assert len(scenario.evidences) == 13
        ev_codes = {e.evidence_code for e in scenario.evidences}
        assert "relatorio_contabil" in ev_codes
        assert "cartao_acesso" in ev_codes
        assert "testemunho_estagiaria" in ev_codes
        assert "auditoria_versoes" in ev_codes

        # Session creation
        session = create_session(scenario.id, db=db)
        s_id = session["id"] if isinstance(session, dict) else session.id
        assert s_id is not None

        overview = get_session_overview(s_id, db=db)
        assert overview["session"]["scenario_id"] == scenario.id
        assert len(overview["suspects"]) == 4

    finally:
        db.close()
