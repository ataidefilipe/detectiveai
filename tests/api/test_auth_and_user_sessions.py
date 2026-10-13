import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import ScenarioModel, UserModel, SessionModel

client = TestClient(app)


def test_auth_config():
    response = client.get("/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert "mock_available" in data
    assert data["mock_available"] is True


def test_auth_mock_login_and_me():
    # 1. Login mock
    login_resp = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "sherlock@detective.ai",
        "mock_name": "Sherlock Holmes"
    })
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "sherlock@detective.ai"
    assert data["user"]["name"] == "Sherlock Holmes"
    token = data["access_token"]

    # 2. Test /auth/me sem token -> 401
    unauth_resp = client.get("/auth/me")
    assert unauth_resp.status_code == 401

    # 3. Test /auth/me com token -> 200
    auth_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_resp.status_code == 200
    me = auth_resp.json()
    assert me["email"] == "sherlock@detective.ai"
    assert me["name"] == "Sherlock Holmes"


def test_user_session_isolation_and_delete():
    from tests.conftest import TestingSessionLocal
    # 1. Obter cenário existente ou criar
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(scenario_code="test_scen_auth", title="Caso Teste Auth", culprit_id=1)
        db.add(scenario)
        db.commit()
        scenario_id = scenario.id
    finally:
        db.close()

    # 2. Criar dois usuários diferentes
    resp_u1 = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "user1@test.com",
        "mock_name": "User One"
    })
    token1 = resp_u1.json()["access_token"]
    u1_id = resp_u1.json()["user"]["id"]

    resp_u2 = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "user2@test.com",
        "mock_name": "User Two"
    })
    token2 = resp_u2.json()["access_token"]
    u2_id = resp_u2.json()["user"]["id"]

    # 3. User 1 cria uma sessão
    create_resp1 = client.post(
        "/sessions",
        json={"scenario_id": scenario_id},
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert create_resp1.status_code == 200
    session1_id = create_resp1.json()["session_id"]
    assert create_resp1.json()["user_id"] == u1_id

    # 4. User 1 lista sessões -> deve conter session1
    list_u1 = client.get("/sessions", headers={"Authorization": f"Bearer {token1}"})
    assert list_u1.status_code == 200
    ids_u1 = [s["id"] for s in list_u1.json()]
    assert session1_id in ids_u1

    # 5. User 2 lista sessões -> NÃO deve conter session1
    list_u2 = client.get("/sessions", headers={"Authorization": f"Bearer {token2}"})
    assert list_u2.status_code == 200
    ids_u2 = [s["id"] for s in list_u2.json()]
    assert session1_id not in ids_u2

    # 6. User 2 tenta apagar sessão do User 1 -> 403 Forbidden
    del_forbidden = client.delete(
        f"/sessions/{session1_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert del_forbidden.status_code == 403

    # 7. User 1 apaga sua própria sessão -> 200 OK
    del_ok = client.delete(
        f"/sessions/{session1_id}",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert del_ok.status_code == 200

    # 8. Sessão não existe mais na listagem do User 1
    list_after = client.get("/sessions", headers={"Authorization": f"Bearer {token1}"})
    ids_after = [s["id"] for s in list_after.json()]
    assert session1_id not in ids_after


def test_admin_role_and_user_management():
    # 1. Login como admin via is_admin=True
    resp_admin = client.post("/auth/google", json={
        "is_mock": True,
        "is_admin": True,
        "mock_email": "admin@detective.ai",
        "mock_name": "Admin Chefe"
    })
    assert resp_admin.status_code == 200
    admin_data = resp_admin.json()
    assert admin_data["user"]["role"] == "admin"
    admin_token = admin_data["access_token"]

    # 2. Login como player comum
    resp_player = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "common_player@test.com",
        "mock_name": "Common Player"
    })
    assert resp_player.status_code == 200
    player_data = resp_player.json()
    assert player_data["user"]["role"] == "player"
    player_token = player_data["access_token"]
    player_id = player_data["user"]["id"]

    # 3. Player tenta listar /auth/users -> 403 Forbidden
    resp_forbidden = client.get("/auth/users", headers={"Authorization": f"Bearer {player_token}"})
    assert resp_forbidden.status_code == 403

    # 4. Admin lista /auth/users -> 200 OK
    resp_users = client.get("/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_users.status_code == 200
    users_list = resp_users.json()
    assert any(u["id"] == player_id for u in users_list)

    # 5. Player tenta promover outro -> 403 Forbidden
    resp_patch_forbidden = client.patch(
        f"/auth/users/{player_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {player_token}"}
    )
    assert resp_patch_forbidden.status_code == 403

    # 6. Admin promove player -> 200 OK
    resp_patch_ok = client.patch(
        f"/auth/users/{player_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_patch_ok.status_code == 200
    assert resp_patch_ok.json()["role"] == "admin"


def test_admin_session_management():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        scenario = ScenarioModel(scenario_code="test_scen_admin", title="Caso Admin", culprit_id=1)
        db.add(scenario)
        db.commit()
        scenario_id = scenario.id
    finally:
        db.close()

    # Criar player e admin
    resp_p = client.post("/auth/google", json={
        "is_mock": True,
        "mock_email": "player_case@test.com",
        "mock_name": "Player Case"
    })
    p_token = resp_p.json()["access_token"]

    resp_a = client.post("/auth/google", json={
        "is_mock": True,
        "is_admin": True,
        "mock_email": "admin@detective.ai",
        "mock_name": "Admin Inspector"
    })
    a_token = resp_a.json()["access_token"]

    # Player cria sessão
    create_resp = client.post(
        "/sessions",
        json={"scenario_id": scenario_id},
        headers={"Authorization": f"Bearer {p_token}"}
    )
    session_id = create_resp.json()["session_id"]

    # Admin consulta all_sessions=true -> deve ver a sessão do player com dados do usuário
    resp_admin_list = client.get("/sessions?all_sessions=true", headers={"Authorization": f"Bearer {a_token}"})
    assert resp_admin_list.status_code == 200
    sessions = resp_admin_list.json()
    found = next((s for s in sessions if s["id"] == session_id), None)
    assert found is not None
    assert found["user_email"] == "player_case@test.com"
    assert found["user_name"] == "Player Case"

    # Admin consegue apagar a sessão do player -> 200 OK
    del_admin_resp = client.delete(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {a_token}"})
    assert del_admin_resp.status_code == 200
