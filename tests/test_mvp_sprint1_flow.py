import os
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal
from unittest.mock import patch

from app.main import app
from app.infra.db_models import ScenarioModel, SuspectModel, EvidenceModel
from app.services.scenario_loader import load_scenario_from_json
from app.api.schemas.chat import StateTransitionResult, NpcShift, ConversationEffect


def test_mvp_sprint1_flow_end_to_end():
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

        evidence_cafe = db.query(EvidenceModel).filter(
            EvidenceModel.name == "Café Derramado"
        ).first()

        evidence_testemunho = db.query(EvidenceModel).filter(
            EvidenceModel.name == "Testemunho da Estagiária"
        ).first()

        evidence_cartao.related_topic_id = "fraude"

        mandatory_ids = scenario.required_evidence_ids
        
        scenario_id = scenario.id
        marina_id = marina.id
        evidence_relatorio_id = evidence_relatorio.id
        evidence_cartao_id = evidence_cartao.id
        evidence_cafe_id = evidence_cafe.id
        evidence_testemunho_id = evidence_testemunho.id
        
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
    # 2.1 Criar Topic State para "faca"
    # -------------------------
    # Como piloto.json não carrega tópicos por padrão e precisamos testar detecção, criamos o state localmente
    db = SessionLocal()
    from app.infra.db_models import SessionSuspectTopicStateModel
    db.add(SessionSuspectTopicStateModel(session_id=session_id, suspect_id=marina_id, topic_id="faca"))
    db.commit()
    db.close()

    # -------------------------
    # 3. Turno 1 - Vago (MVP-001)
    # -------------------------
    # Pergunta sem tópico detectável e sem evidência
    with patch("app.services.interrogation_turn_service.analyze_message") as mock_analysis:
        from app.api.schemas.chat import MessageAnalysisResult, MessageIntent, SensitivityLevel
        mock_analysis.return_value = MessageAnalysisResult(
            intent=MessageIntent.ask,
            detected_topic_ids=[],
            sensitivity_hit=SensitivityLevel.none
        )
        
        turn1_resp = client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "E aí, o que você acha da vida?"}
        )
        assert turn1_resp.status_code == 200
        turn1_data = turn1_resp.json()
        
        assert turn1_data["narrative_feedback"]["guidance"] == "A pergunta foi muito aberta e não obteve um foco claro."

    # -------------------------
    # 4. Turno 2 - Contexto Promissor (MVP-004)
    # -------------------------
    # Tópico sensível hit + evidência errada = out_of_context atenuado
    with patch("app.services.interrogation_turn_service.analyze_message") as mock_analysis:
        mock_analysis.return_value = MessageAnalysisResult(
            intent=MessageIntent.confront,
            detected_topic_ids=["faca"],
            sensitive_topic_ids=["faca"],
            sensitivity_hit=SensitivityLevel.high
        )
        
        # O cartão não deve provar fraude financeira diretamente (out_of_context forzado em db)
        turn2_resp = client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "Fraude com este cartão!", "evidence_id": evidence_cartao_id}
        )
        if turn2_resp.status_code != 200:
            print(f"TURN 2 FAILED: {turn2_resp.status_code} - {turn2_resp.text}")
        assert turn2_resp.status_code == 200
        turn2_data = turn2_resp.json()
        print("TURN 2 DATA: ", turn2_data)
        
        assert turn2_data["evidence_effect"] == "out_of_context"
        assert turn2_data["narrative_feedback"]["guidance"] == "A direção é boa, mas essa ligação ainda não faz sentido para o suspeito."

    # -------------------------
    # 5. Turno 3 - Reaction Only (MVP-002)
    # -------------------------
    with patch("app.services.interrogation_turn_service.resolve_turn_state") as mock_resolve, \
         patch("app.services.interrogation_turn_service.analyze_message") as mock_analysis:
             
        mock_analysis.return_value = MessageAnalysisResult(
            intent=MessageIntent.confront,
            detected_topic_ids=["faca"],
            sensitive_topic_ids=["faca"],
            sensitivity_hit=SensitivityLevel.high
        )
        mock_resolve.return_value = StateTransitionResult(
            conversation_effect=ConversationEffect.sensitive_touch,
            npc_shift=NpcShift.pressured,
            state_deltas={}
        )
        
        # Enviando cartão de novo, mas forçando reação via mocks. 
        # (na vida real reaction_only checa se NpcShift == pressured + evidence_effect!=out_of_context)
        # Vamos passar None para a evidência para focar no fluxo, ou uma certa sem out of context direto.
        # For reaction_only we actually DO need an evidence_id to hit the block inside service!
        # And we need apply_evidence to return 'none' or 'duplicate'
        turn3_resp = client.post(
            f"/sessions/{session_id}/suspects/{marina_id}/messages",
            json={"text": "E esse café espalhado?!", "evidence_id": evidence_cafe_id} 
        )
        
        assert turn3_resp.status_code == 200
        turn3_data = turn3_resp.json()
        assert turn3_data["evidence_effect"] == "reaction_only"
        assert turn3_data["narrative_feedback"]["suspect_reaction"] == "pressionado"

    # -------------------------
    # 6. Turno 4 - Golden Path Real
    # -------------------------
    # Entregar a evidência certa que prova o core secret principal
    turn4_resp = client.post(
        f"/sessions/{session_id}/suspects/{marina_id}/messages",
        json={"text": "Você alterou o relatório!", "evidence_id": evidence_relatorio_id}
    )
    assert turn4_resp.status_code == 200
    turn4_data = turn4_resp.json()
    assert turn4_data["evidence_effect"] == "revealed_secret"
    
    # -------------------------
    # 6.1 Revelar restantes para fechar o suspeito
    # -------------------------
    turn5_resp = client.post(
        f"/sessions/{session_id}/suspects/{marina_id}/messages",
        json={"text": "Aqui está o cartão, assuma!", "evidence_id": evidence_cartao_id}
    )
    assert turn5_resp.status_code == 200

    turn6_resp = client.post(
        f"/sessions/{session_id}/suspects/{marina_id}/messages",
        json={"text": "Temos uma testemunha.", "evidence_id": evidence_testemunho_id}
    )
    assert turn6_resp.status_code == 200

    # -------------------------
    # 7. Acusação Final
    # -------------------------
    # Ainda usamos a API de acusação antiga que aprova só com as suspeitas ID
    resp_accuse = client.post(
        f"/sessions/{session_id}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": mandatory_ids,
            "motive_key": "financial_gain"
        }
    )

    assert resp_accuse.status_code == 200
    assert resp_accuse.json()["result_type"] == "correct"

    # -------------------------
    # 8. Acusação Final (Erro de Motivação = Partial) MVP-007 + MVP-008
    # -------------------------
    # (Here we are mocking another session manually just to reuse the database variables or creating a second accuse logic if the session wasn't closed.
    # Since in reality a session closes after one request, we will cheat and un-close it inside DB just for the test, or just test if we receive a partial result on a new session)
    # Let's create a new quick session for the wrong motive check
    resp2 = client.post("/sessions", json={"scenario_id": scenario_id})
    session_id_2 = resp2.json()["session_id"]
    
    # We must mark all required evidences as used
    db = SessionLocal()
    from app.infra.db_models import SessionEvidenceUsageModel
    for evid_id in mandatory_ids:
        db.add(SessionEvidenceUsageModel(session_id=session_id_2, suspect_id=marina_id, evidence_id=evid_id))
    db.commit()
    db.close()
    
    resp_accuse_partial = client.post(
        f"/sessions/{session_id_2}/accuse",
        json={
            "suspect_id": marina_id,
            "evidence_ids": mandatory_ids,
            "motive_key": "revenge" # Errado
        }
    )

    assert resp_accuse_partial.status_code == 200
    assert resp_accuse_partial.json()["result_type"] == "partial"
    assert resp_accuse_partial.json()["motive_result"] == "wrong"
