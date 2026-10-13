import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel, SuspectModel, SessionModel, 
    EvidenceModel, SecretModel
)

client = TestClient(app)


@pytest.fixture
def setup_full_cycle_case():
    db = SessionLocal()
    scenario = ScenarioModel(
        scenario_code="full_cycle_noir_test",
        title="O Enigma da Mansão Sombria",
        true_motive_key="blackmail"
    )
    db.add(scenario)
    db.commit()

    suspect = SuspectModel(
        scenario_id=scenario.id,
        suspect_code="vicente_noir",
        name="Vicente Silva",
        role_title="Mordomo Suspeito",
        claims=[
            {
                "claim_id": "claim_alibi",
                "statement": "Eu estava na despensa às 22h.",
                "associated_evidence_codes": ["doc_noir_01"]
            }
        ],
        knowledge_items=[]
    )
    db.add(suspect)
    db.commit()

    scenario.culprit_id = suspect.id

    evidence = EvidenceModel(
        scenario_id=scenario.id,
        evidence_code="doc_noir_01",
        name="Recibo de Farmácia Rasgado",
        description="Comprovante de compra de veneno às 22h05."
    )
    db.add(evidence)
    db.commit()

    scenario.required_evidence_ids = [evidence.id]

    # Secret
    secret = SecretModel(
        suspect_id=suspect.id,
        evidence_id=evidence.id,
        content="Vicente comprou o veneno para chantagear a vítima.",
        is_core=True
    )
    db.add(secret)
    db.commit()

    # Create session via API
    res_session = client.post("/sessions", json={"scenario_id": scenario.id})
    assert res_session.status_code == 200
    session_id = res_session.json()["session_id"]

    yield {
        "session_id": session_id,
        "suspect_id": suspect.id,
        "evidence_id": evidence.id,
        "scenario_id": scenario.id
    }

    db.close()


def test_full_investigation_cycle_integration(setup_full_cycle_case):
    session_id = setup_full_cycle_case["session_id"]
    suspect_id = setup_full_cycle_case["suspect_id"]
    evidence_id = setup_full_cycle_case["evidence_id"]

    # 1. Enviar mensagem de interrogatório confrontando evidência
    msg_res = client.post(
        f"/sessions/{session_id}/suspects/{suspect_id}/messages",
        json={
            "text": "O que você tem a dizer sobre este recibo de veneno?",
            "evidence_id": evidence_id
        }
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert "npc_message" in msg_data

    # 2. Verificar Dossiê Policial (TASK-02)
    dossier_res = client.get(f"/sessions/{session_id}/suspects/{suspect_id}/dossier")
    assert dossier_res.status_code == 200
    dossier_data = dossier_res.json()
    assert dossier_data["name"] == "Vicente Silva"
    assert dossier_data["role_title"] == "Mordomo Suspeito"
    assert len(dossier_data["used_evidences"]) >= 1
    assert dossier_data["used_evidences"][0]["evidence_id"] == evidence_id

    # 3. Verificar Sala de Provas / Evidence Locker (TASK-03)
    ev_res = client.get(f"/sessions/{session_id}/evidences")
    assert ev_res.status_code == 200
    ev_list = ev_res.json()
    assert len(ev_list) >= 1
    target_ev = next(e for e in ev_list if e["id"] == evidence_id)
    assert target_ev["is_used"] is True
    assert len(target_ev["usages"]) >= 1
    assert target_ev["usages"][0]["suspect_name"] == "Vicente Silva"

    # 4. Verificar Mural de Investigação / Whiteboard (TASK-04)
    board_get = client.get(f"/sessions/{session_id}/board")
    assert board_get.status_code == 200
    board_data = board_get.json()["board_data"]
    assert len(board_data["nodes"]) >= 2

    # Salvar customização no mural (adicionar nota e barbante)
    board_data["stickers"].append({
        "id": "sticker-clue-01",
        "text": "Vicente mentiu sobre o horário da farmácia!",
        "color": "pink",
        "x": 300.0,
        "y": 150.0
    })
    board_data["connections"].append({
        "id": "conn-01",
        "from_id": f"suspect-{suspect_id}",
        "to_id": f"evidence-{evidence_id}"
    })

    board_put = client.put(f"/sessions/{session_id}/board", json={"board_data": board_data})
    assert board_put.status_code == 200
    updated_board = board_put.json()["board_data"]
    assert len(updated_board["stickers"]) >= 2
    assert len(updated_board["connections"]) == 1

    # 5. Apresentar Acusação Final (TASK-05 integração)
    accuse_res = client.post(
        f"/sessions/{session_id}/accuse",
        json={
            "suspect_id": suspect_id,
            "motive_key": "blackmail",
            "evidence_ids": [evidence_id]
        }
    )
    assert accuse_res.status_code == 200
    accuse_data = accuse_res.json()
    assert accuse_data["result_type"] == "correct"
    assert accuse_data["chosen_suspect_id"] == accuse_data["real_culprit_id"]
