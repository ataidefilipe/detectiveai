import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SessionEvidenceUsageModel,
    SessionClaimStateModel,
)
from app.services.scenario_loader import load_scenario_from_json

client = TestClient(app)


@pytest.fixture
def test_scenario():
    db = SessionLocal()
    try:
        scenario_path = os.path.join(os.path.dirname(__file__), "../../scenarios/piloto.json")
        scenario_obj = load_scenario_from_json(scenario_path, db=db)
        return scenario_obj.id
    finally:
        db.close()


def test_session_logs_not_found():
    # Sessão inexistente
    resp = client.get("/sessions/99999/logs/turns")
    assert resp.status_code == 404

    resp = client.get("/sessions/99999/logs/verdict")
    assert resp.status_code == 404


def test_get_session_turn_logs_and_prompt_filtering(test_scenario):
    # 1. Cria sessão
    create_resp = client.post("/sessions", json={"scenario_id": test_scenario})
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    # 2. Sem turnos ainda
    logs_resp = client.get(f"/sessions/{session_id}/logs/turns")
    assert logs_resp.status_code == 200
    data = logs_resp.json()
    assert data["session_id"] == session_id
    assert data["total_turns"] == 0
    assert data["turns"] == []

    # 3. Veredito ainda não existe
    verdict_resp = client.get(f"/sessions/{session_id}/logs/verdict")
    assert verdict_resp.status_code == 404

    # 4. Busca suspeitos para obter um suspect_id válido
    suspects_resp = client.get(f"/sessions/{session_id}/suspects")
    assert suspects_resp.status_code == 200
    suspect_id = suspects_resp.json()[0]["suspect_id"]

    # 5. Executa um turno
    msg_resp = client.post(
        f"/sessions/{session_id}/suspects/{suspect_id}/messages",
        json={"text": "Onde você estava na hora do crime?"}
    )
    assert msg_resp.status_code == 200

    # 6. Consulta logs sem prompt (padrão)
    logs_resp = client.get(f"/sessions/{session_id}/logs/turns")
    assert logs_resp.status_code == 200
    data = logs_resp.json()
    assert data["total_turns"] == 1
    turn = data["turns"][0]
    assert turn["session_id"] == session_id
    assert turn["suspect_id"] == suspect_id
    assert turn["turn_number"] == 1
    assert turn["player_text"] == "Onde você estava na hora do crime?"
    assert turn["npc_text"] is not None
    assert turn["prompt"] is None  # omitido por padrão

    # 7. Consulta logs com include_prompt=true
    logs_prompt_resp = client.get(f"/sessions/{session_id}/logs/turns?include_prompt=true")
    assert logs_prompt_resp.status_code == 200
    turn_with_prompt = logs_prompt_resp.json()["turns"][0]
    assert turn_with_prompt["prompt"] is not None

    # 8. Filtro por suspect_id
    logs_filtered = client.get(f"/sessions/{session_id}/logs/turns?suspect_id={suspect_id}")
    assert logs_filtered.status_code == 200
    assert logs_filtered.json()["total_turns"] == 1

    logs_other_suspect = client.get(f"/sessions/{session_id}/logs/turns?suspect_id=9999")
    assert logs_other_suspect.status_code == 200
    assert logs_other_suspect.json()["total_turns"] == 0


def test_get_session_verdict_log(test_scenario):
    # 1. Cria sessão
    create_resp = client.post("/sessions", json={"scenario_id": test_scenario})
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    # 2. Finaliza a sessão simulando veredito
    from app.services.session_finalize_service import finalize_session
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(ScenarioModel.id == test_scenario).first()
        culprit_id = scenario.culprit_id
        
        # Preparar evidência para B3 se necessário ou acusar
        finalize_session(
            session_id=session_id,
            chosen_suspect_id=culprit_id,
            evidence_ids=[],
            motive_key=scenario.true_motive_key,
            db=db
        )
    finally:
        db.close()

    # 3. Consulta GET /sessions/{session_id}/logs/verdict
    resp = client.get(f"/sessions/{session_id}/logs/verdict")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["scenario_id"] == test_scenario
    assert data["chosen_suspect_id"] == culprit_id
    assert data["result_type"] in ("correct", "partial", "wrong")
    assert data["verdict"] is not None
    assert data["session_summary"] is not None
