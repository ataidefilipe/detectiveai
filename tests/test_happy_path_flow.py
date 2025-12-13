import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.infra.db_models import Base, ScenarioModel, SuspectModel, EvidenceModel
from app.services.scenario_loader import load_scenario_from_json


# ---------------------------------------------------------------------
# Infra de DB temporário
# ---------------------------------------------------------------------

def patch_db_to_temp_sqlite(db_path: str):
    import app.infra.db as db_module

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(bind=engine)

    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


# ---------------------------------------------------------------------
# Teste integrado – Happy Path
# ---------------------------------------------------------------------

def test_happy_path_piloto_end_to_end():
    """
    Fluxo completo:
      - carrega piloto.json
      - cria sessão
      - interroga Marina com 2 evidências core
      - acusa Marina com todas as evidências obrigatórias
      - recebe result_type="correct"
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_game.db")
        SessionLocal = patch_db_to_temp_sqlite(db_path)

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

            # Marina é a culpada
            marina = (
                db.query(SuspectModel)
                .filter(SuspectModel.name == "Marina Souza")
                .first()
            )
            assert marina is not None

            # Evidências
            evidence_relatorio = (
                db.query(EvidenceModel)
                .filter(EvidenceModel.name == "Relatório Contábil Alterado")
                .first()
            )
            evidence_cartao = (
                db.query(EvidenceModel)
                .filter(EvidenceModel.name == "Cartão de Acesso de Marina")
                .first()
            )
            evidence_testemunho = (
                db.query(EvidenceModel)
                .filter(EvidenceModel.name == "Testemunho da Estagiária")
                .first()
            )

            assert all([evidence_relatorio, evidence_cartao, evidence_testemunho])

            mandatory_ids = scenario.required_evidence_ids
            assert set(mandatory_ids) == {
                evidence_relatorio.id,
                evidence_cartao.id,
                evidence_testemunho.id
            }

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
        # 3. Confronto 1 – Relatório
        # -------------------------
        resp = client.post(
            f"/sessions/{session_id}/suspects/{marina.id}/messages",
            json={
                "text": "Explique esse relatório.",
                "evidence_id": evidence_relatorio.id
            }
        )
        assert resp.status_code == 200
        assert len(resp.json()["revealed_secrets"]) >= 1

        # -------------------------
        # 4. Confronto 2 – Cartão
        # -------------------------
        resp = client.post(
            f"/sessions/{session_id}/suspects/{marina.id}/messages",
            json={
                "text": "E sobre seu cartão de acesso?",
                "evidence_id": evidence_cartao.id
            }
        )
        assert resp.status_code == 200

        # -------------------------
        # 5. Acusação final
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

        assert result["status"] == "finished"
        assert result["result_type"] == "correct"
        assert result["real_culprit_id"] == marina.id
