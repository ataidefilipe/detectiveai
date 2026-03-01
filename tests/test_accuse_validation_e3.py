import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal
from app.main import app
from app.infra.db_models import SuspectModel, EvidenceModel

client = TestClient(app)

def test_cannot_accuse_with_evidence_used_on_wrong_suspect():
    import os
    from app.services.scenario_loader import load_scenario_from_json

    db = TestingSessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        scenario = load_scenario_from_json(scenario_path, db=db)
        
        marina = db.query(SuspectModel).filter(SuspectModel.name == "Marina Souza").first()
        outros_suspeitos = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.id != marina.id
        ).all()
        outro_suspeito = outros_suspeitos[0]
        
        relatorio = db.query(EvidenceModel).filter(EvidenceModel.scenario_id == scenario.id).first()
        
        scenario_id = scenario.id
        marina_id = marina.id
        outro_suspeito_id = outro_suspeito.id
        relatorio_id = relatorio.id
    finally:
        db.close()

    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    test_session_id = resp.json()["session_id"]

    # Use a evidência no chat com a Marina
    resp_chat = client.post(
        f"/sessions/{test_session_id}/suspects/{marina_id}/messages",
        json={"text": "Explique isso.", "evidence_id": relatorio_id}
    )
    assert resp_chat.status_code == 200

    # Tenta usar essa evidência para acusar o Outro Suspeito
    resp = client.post(
        f"/sessions/{test_session_id}/accuse",
        json={
            "suspect_id": outro_suspeito_id,
            "evidence_ids": [relatorio_id]
        }
    )

    # Como a evidência não foi usada CONTRA o suspeito acusado, deve falhar
    assert resp.status_code == 409
    assert "was not used against the accused suspect" in resp.json()["detail"]
