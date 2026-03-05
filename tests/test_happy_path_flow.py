import os
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal

from app.main import app
from app.infra.db_models import Base, ScenarioModel, SuspectModel, EvidenceModel, SecretModel
from app.services.scenario_loader import load_scenario_from_json


def test_happy_path_piloto_end_to_end():

    SessionLocal = TestingSessionLocal

    # -------------------------
    # 1. Carregar cenário piloto
    # -------------------------
    db = SessionLocal()
    try:
        scenario_path = os.path.join("scenarios", "piloto.json")
        assert os.path.exists(scenario_path), "piloto.json não encontrado"

        load_scenario_from_json(scenario_path, db=db)

        scenario = db.query(ScenarioModel).first()
        assert scenario is not None

        marina = db.query(SuspectModel).filter(
            SuspectModel.name == "Marina Souza"
        ).first()
        assert marina is not None

        evidence_relatorio = db.query(EvidenceModel).filter(
            EvidenceModel.name == "Relatório Contábil Alterado"
        ).first()

        evidence_cartao = db.query(EvidenceModel).filter(
            EvidenceModel.name == "Cartão de Acesso de Marina"
        ).first()

        evidence_testemunho = db.query(EvidenceModel).filter(
            EvidenceModel.name == "Testemunho da Estagiária"
        ).first()

        scenario_id = scenario.id
        marina_id = marina.id
        evidence_relatorio_id = evidence_relatorio.id
        evidence_cartao_id = evidence_cartao.id
        evidence_testemunho_id = evidence_testemunho.id
        
        mandatory_ids = scenario.required_evidence_ids
        
        # Inject secrets so evidence usage counts as effective
        secret_cartao = SecretModel(suspect_id=marina_id, evidence_id=evidence_cartao_id, content="Secret Cartao")
        secret_testemunha = SecretModel(suspect_id=marina_id, evidence_id=evidence_testemunho_id, content="Secret Testemunha")
        db.add_all([secret_cartao, secret_testemunha])
        db.commit()

    finally:
        db.close()

    client = TestClient(app)

    # -------------------------
    # 2. Criar sessão
    # -------------------------
    resp = client.post("/sessions", json={"scenario_id": scenario_id})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # -------------------------
    # 3. Confrontos
    # -------------------------
    
    # Criar states localmente para passar no Topic Guard
    db = SessionLocal()
    from app.infra.db_models import SessionSuspectTopicStateModel
    db.add(SessionSuspectTopicStateModel(session_id=session_id, suspect_id=marina_id, topic_id="fraude"))
    db.commit()
    db.close()
    
    from unittest.mock import patch
    from app.api.schemas.chat import MessageAnalysisResult, MessageIntent, SensitivityLevel

    with patch("app.services.interrogation_turn_service.analyze_message") as mock_analysis:
        mock_analysis.return_value = MessageAnalysisResult(
            intent=MessageIntent.confront,
            detected_topic_ids=["fraude"],
            sensitive_topic_ids=[],
            sensitivity_hit=SensitivityLevel.none
        )
        client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "Explique isso.", "evidence_id": evidence_relatorio_id}
        )

        client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "E o cartão da fraude?", "evidence_id": evidence_cartao_id}
        )
        
        client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "E a testemunha?", "evidence_id": evidence_testemunho_id}
        )

    # -------------------------
    # 4. Acusação final
    # -------------------------
    resp = client.post(
        f"/sessions/{session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": mandatory_ids,
            "motive_key": "financial_gain"
        }
    )

    assert resp.status_code == 200
    result = resp.json()

    assert result["result_type"] == "correct"
