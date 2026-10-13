import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import TestingSessionLocal
from app.infra.db_models import ScenarioModel, SuspectModel, SessionModel, UserModel

client = TestClient(app)


def test_ai_settings_unauthorized():
    response = client.get("/auth/ai-settings")
    assert response.status_code == 401


def test_ai_settings_get_default():
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "detetive_ai_test@example.com",
        "mock_name": "Agente Teste"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/auth/ai-settings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_custom_key"] is False
    assert data["masked_key"] is None
    assert data["default_chat_model"] == "gpt-6-luna"
    assert data["default_classifier_model"] == "gpt-6-luna"
    assert data["chat_model"] == "gpt-6-luna"
    assert data["classifier_model"] == "gpt-6-luna"
    assert "gpt-6-luna" in data["available_models"]
    assert "gpt-5-mini" in data["available_models"]


def test_ai_settings_validation_rejects_non_openai_key():
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "detetive_val@example.com",
        "mock_name": "Agente Validação"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Chave que não começa com sk-
    resp = client.put(
        "/auth/ai-settings",
        json={"api_key": "invalid-key-not-openai"},
        headers=headers
    )
    assert resp.status_code == 400
    assert "apenas chaves da openai são aceitas" in resp.json()["detail"].lower()


def test_ai_settings_validation_rejects_invalid_model():
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "detetive_model_val@example.com",
        "mock_name": "Agente Modelo"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Modelo de conversa inválido
    resp_chat = client.put(
        "/auth/ai-settings",
        json={"chat_model": "claude-3-opus"},
        headers=headers
    )
    assert resp_chat.status_code == 400
    assert "conversa inválido" in resp_chat.json()["detail"].lower()

    # Modelo de categorização inválido
    resp_class = client.put(
        "/auth/ai-settings",
        json={"classifier_model": "gemini-1.5-pro"},
        headers=headers
    )
    assert resp_class.status_code == 400
    assert "categorização inválido" in resp_class.json()["detail"].lower()


def test_ai_settings_save_and_clear_key():
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "detetive_save@example.com",
        "mock_name": "Agente Salvar"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Salva chave válida e escolhe modelos diferentes para conversa e categorização
    save_resp = client.put(
        "/auth/ai-settings",
        json={
            "api_key": "sk-proj-testkey123456",
            "chat_model": "gpt-5-mini",
            "classifier_model": "gpt-6-luna"
        },
        headers=headers
    )
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["has_custom_key"] is True
    assert save_data["chat_model"] == "gpt-5-mini"
    assert save_data["classifier_model"] == "gpt-6-luna"
    assert "sk-...3456" in save_data["masked_key"]

    # Verifica persistência no GET
    get_resp = client.get("/auth/ai-settings", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["has_custom_key"] is True
    assert get_resp.json()["chat_model"] == "gpt-5-mini"
    assert get_resp.json()["classifier_model"] == "gpt-6-luna"
    assert get_resp.json()["masked_key"] == save_data["masked_key"]

    # Limpa chave própria
    clear_resp = client.put(
        "/auth/ai-settings",
        json={"api_key": ""},
        headers=headers
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["has_custom_key"] is False
    assert clear_resp.json()["masked_key"] is None


def test_interrogation_turn_uses_stored_user_api_key():
    """Verifica que quando o usuário tem chave configurada, ela é passada para o adapter e classifier com seus respectivos modelos."""
    db = TestingSessionLocal()
    try:
        scen = ScenarioModel(
            scenario_code="scen_ai_key_test",
            title="Caso Chave OpenAI",
            topics=[{"id": "alibi", "name": "Álibi", "keywords": ["onde", "estava"]}],
            culprit_id=1
        )
        db.add(scen)
        db.flush()

        susp = SuspectModel(
            scenario_id=scen.id,
            name="Suspeito Chave",
            personality="tenso",
            initial_statement="Não fiz nada."
        )
        db.add(susp)
        db.commit()
        scenario_id = scen.id
        suspect_id = susp.id
    finally:
        db.close()

    # Cria usuário com chave OpenAI e modelos configurados
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "detetive_ai_turn@example.com",
        "mock_name": "Agente Turno"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.put(
        "/auth/ai-settings",
        json={
            "api_key": "sk-user-custom-key-12345",
            "chat_model": "gpt-5-mini",
            "classifier_model": "gpt-6-luna"
        },
        headers=headers
    )

    # Cria sessão com esse usuário
    create_resp = client.post(
        "/sessions",
        json={"scenario_id": scenario_id},
        headers=headers
    )
    session_id = create_resp.json()["session_id"]

    # Mocka OpenAI client para verificar inicialização com as credenciais do usuário
    with patch("app.services.ai_adapter_openai.OpenAI") as mock_openai_cls, \
         patch("app.services.message_classifier_openai.OpenAI") as mock_classifier_cls:
        
        mock_client_instance = MagicMock()
        mock_openai_cls.return_value = mock_client_instance
        mock_classifier_cls.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.output_text = (
            '{"intent": "ask", "primary_topic_id": "alibi", "mentioned_topics": ["alibi"], '
            '"tone": "neutral", "patience_delta": -1, "pressure_delta": 2, "sensitivity_hit": "none", '
            '"reasoning": "perguntou onde estava"}'
        )
        mock_client_instance.responses.create.return_value = mock_response

        # Envia mensagem no interrogatório com o token do usuário
        msg_resp = client.post(
            f"/sessions/{session_id}/suspects/{suspect_id}/messages",
            json={"text": "Onde você estava ontem à noite?"},
            headers=headers
        )
        assert msg_resp.status_code == 200
        data = msg_resp.json()
        assert data["npc_message"]["text"] == mock_response.output_text

        # Verifica que OpenAI adapter e classifier foram inicializados com a chave do usuário
        mock_openai_cls.assert_called_with(api_key="sk-user-custom-key-12345")
        mock_classifier_cls.assert_called_with(api_key="sk-user-custom-key-12345", timeout=6)
