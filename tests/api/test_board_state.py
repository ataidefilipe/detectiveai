import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import ScenarioModel, SuspectModel, SessionModel, EvidenceModel

client = TestClient(app)


@pytest.fixture
def setup_board_test_data():
    db = SessionLocal()
    scenario = ScenarioModel(scenario_code="board_test_case", title="Board Test Scenario")
    db.add(scenario)
    db.commit()

    suspect1 = SuspectModel(
        scenario_id=scenario.id,
        suspect_code="suspect_alpha",
        name="Carlos Mendes",
        role_title="Gerente Financeiro",
        claims=[],
        knowledge_items=[]
    )
    db.add(suspect1)
    db.commit()

    ev1 = EvidenceModel(
        scenario_id=scenario.id,
        evidence_code="ev_board_01",
        name="Chave Mestra",
        description="Encontrada no cofre aberto."
    )
    db.add(ev1)
    db.commit()

    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.commit()

    yield {
        "session_id": session.id,
        "suspect_id": suspect1.id,
        "evidence_id": ev1.id,
        "db": db
    }

    db.close()


def test_get_board_initial_layout(setup_board_test_data):
    session_id = setup_board_test_data["session_id"]
    response = client.get(f"/sessions/{session_id}/board")
    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == session_id
    board_data = data["board_data"]
    assert "nodes" in board_data
    assert "connections" in board_data
    assert "stickers" in board_data

    # Deve conter pelo menos o nó do suspeito e da evidência
    nodes = board_data["nodes"]
    assert len(nodes) >= 2
    types = [n["type"] for n in nodes]
    assert "suspect" in types
    assert "evidence" in types

    # Deve conter sticker de boas-vindas
    assert len(board_data["stickers"]) >= 1


def test_put_and_get_board_persistence(setup_board_test_data):
    session_id = setup_board_test_data["session_id"]
    suspect_id = setup_board_test_data["suspect_id"]
    evidence_id = setup_board_test_data["evidence_id"]

    # Estado customizado modificado pelo jogador
    payload = {
        "board_data": {
            "nodes": [
                {
                    "id": f"suspect-{suspect_id}",
                    "type": "suspect",
                    "ref_id": suspect_id,
                    "title": "Carlos Mendes",
                    "subtitle": "Gerente Financeiro",
                    "image_url": "/static/assets/templates/suspect-template.svg",
                    "x": 150.0,
                    "y": 200.0
                },
                {
                    "id": f"evidence-{evidence_id}",
                    "type": "evidence",
                    "ref_id": evidence_id,
                    "title": "Chave Mestra",
                    "subtitle": "EV-01",
                    "image_url": "/static/assets/templates/evidence-template.svg",
                    "x": 420.0,
                    "y": 300.0
                }
            ],
            "connections": [
                {
                    "id": f"conn-suspect-{suspect_id}-evidence-{evidence_id}",
                    "from_id": f"suspect-{suspect_id}",
                    "to_id": f"evidence-{evidence_id}",
                    "label": "Acesso ao cofre"
                }
            ],
            "stickers": [
                {
                    "id": "sticker-101",
                    "text": "Hipótese: ele usou a chave às 22h",
                    "color": "pink",
                    "x": 600.0,
                    "y": 250.0
                }
            ]
        }
    }

    # Salva via PUT
    put_res = client.put(f"/sessions/{session_id}/board", json=payload)
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert len(put_data["board_data"]["connections"]) == 1
    assert put_data["board_data"]["connections"][0]["from_id"] == f"suspect-{suspect_id}"

    # Recarrega via GET e verifica persistência integral
    get_res = client.get(f"/sessions/{session_id}/board")
    assert get_res.status_code == 200
    get_data = get_res.json()

    assert len(get_data["board_data"]["nodes"]) == 2
    assert get_data["board_data"]["nodes"][0]["x"] == 150.0
    assert len(get_data["board_data"]["connections"]) == 1
    assert get_data["board_data"]["connections"][0]["to_id"] == f"evidence-{evidence_id}"
    assert len(get_data["board_data"]["stickers"]) == 1
    assert get_data["board_data"]["stickers"][0]["color"] == "pink"


def test_board_not_found():
    response = client.get("/sessions/999999/board")
    assert response.status_code == 404
