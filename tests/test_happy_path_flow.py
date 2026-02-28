import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.infra.db_models import Base, ScenarioModel, SuspectModel, EvidenceModel
from app.services.scenario_loader import load_scenario_from_json


def patch_db_to_memory_sqlite():
    import app.infra.db as db_module

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    TestingSessionLocal = sessionmaker(bind=engine)

    import app.api.sessions as api_sessions
    import app.services.chat_service as chat_service
    import app.services.secret_service as secret_service
    import app.services.session_service as session_service
    import app.services.session_finalize_service as session_finalize_service

    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal
    api_sessions.SessionLocal = TestingSessionLocal
    chat_service.SessionLocal = TestingSessionLocal
    secret_service.SessionLocal = TestingSessionLocal
    session_service.SessionLocal = TestingSessionLocal
    session_finalize_service.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_happy_path_piloto_end_to_end():

    SessionLocal = patch_db_to_memory_sqlite()

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

        mandatory_ids = scenario.required_evidence_ids

    finally:
        db.close()

    client = TestClient(app)

    # -------------------------
    # 2. Criar sessão
    # -------------------------
    resp = client.post("/sessions", json={"scenario_id": scenario.id})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # -------------------------
    # 3. Confrontos
    # -------------------------
    client.post(
        f"/sessions/{session_id}/suspects/{marina.id}/messages",
        json={"text": "Explique isso.", "evidence_id": evidence_relatorio.id}
    )

    client.post(
        f"/sessions/{session_id}/suspects/{marina.id}/messages",
        json={"text": "E o cartão?", "evidence_id": evidence_cartao.id}
    )

    # -------------------------
    # 4. Acusação final
    # -------------------------
    resp = client.post(
        f"/sessions/{session_id}/accuse",
        json={
            "suspect_id": marina.id,
            "evidence_ids": mandatory_ids
        }
    )

    assert resp.status_code == 200
    result = resp.json()

    assert result["result_type"] == "correct"
