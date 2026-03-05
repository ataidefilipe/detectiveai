import pytest
from app.services.verdict_service import evaluate_verdict
from app.infra.db import SessionLocal, Base, init_db
from app.infra.db_models import ScenarioModel, SessionModel, SuspectModel, EvidenceModel, SessionEvidenceUsageModel
from app.services.scenario_loader import load_scenario_from_json
import os

@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    init_db()

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        scenario_path = os.path.join(os.path.dirname(__file__), "../../scenarios/piloto.json")
        load_scenario_from_json(scenario_path, db=db)
        yield db
    finally:
        db.close()

def test_evaluate_verdict_correct(db_session):
    scenario = db_session.query(ScenarioModel).first()
    
    # Identify objects
    marina = db_session.query(SuspectModel).filter_by(name="Marina Souza", scenario_id=scenario.id).first()
    relatorio = db_session.query(EvidenceModel).filter_by(name="Relatório Contábil Alterado", scenario_id=scenario.id).first()
    cartao = db_session.query(EvidenceModel).filter_by(name="Cartão de Acesso de Marina", scenario_id=scenario.id).first()
    testemunho = db_session.query(EvidenceModel).filter_by(name="Testemunho da Estagiária", scenario_id=scenario.id).first()
    
    # Create simple session
    session = SessionModel(scenario_id=scenario.id, status="in_progress")
    db_session.add(session)
    db_session.commit()
    
    # We need to simulate that the player USED the evidences against Marina
    usage1 = SessionEvidenceUsageModel(session_id=session.id, suspect_id=marina.id, evidence_id=relatorio.id, was_effective=True)
    usage2 = SessionEvidenceUsageModel(session_id=session.id, suspect_id=marina.id, evidence_id=cartao.id, was_effective=True)
    usage3 = SessionEvidenceUsageModel(session_id=session.id, suspect_id=marina.id, evidence_id=testemunho.id, was_effective=True)
    db_session.add_all([usage1, usage2, usage3])
    db_session.commit()

    verdict = evaluate_verdict(
        session_id=session.id,
        chosen_suspect_id=marina.id,
        evidence_ids=[relatorio.id, cartao.id, testemunho.id],
        motive_key="financial_gain",
        db=db_session
    )

    assert verdict["result_type"] == "correct"
    assert verdict["motive_result"] == "correct"
    assert len(verdict["reason_codes"]) == 0

def test_evaluate_verdict_partial_wrong_motivation(db_session):
    scenario = db_session.query(ScenarioModel).first()
    marina = db_session.query(SuspectModel).filter_by(name="Marina Souza", scenario_id=scenario.id).first()
    
    # Get required evidences
    req_evidence_names = ["Relatório Contábil Alterado", "Cartão de Acesso de Marina", "Testemunho da Estagiária"]
    req_evidences = db_session.query(EvidenceModel).filter(
        EvidenceModel.name.in_(req_evidence_names), EvidenceModel.scenario_id == scenario.id
    ).all()
    req_evidence_ids = [e.id for e in req_evidences]

    session = SessionModel(scenario_id=scenario.id, status="in_progress")
    db_session.add(session)
    db_session.commit()
    
    for eid in req_evidence_ids:
        usage = SessionEvidenceUsageModel(session_id=session.id, suspect_id=marina.id, evidence_id=eid, was_effective=True)
        db_session.add(usage)
    db_session.commit()

    verdict = evaluate_verdict(
        session_id=session.id,
        chosen_suspect_id=marina.id,
        evidence_ids=req_evidence_ids,
        motive_key="revenge", # Erro aqui! Retornara partial em result_type
        db=db_session
    )

    assert verdict["result_type"] == "partial"
    assert verdict["motive_result"] == "wrong"
    assert "wrong_motive" in verdict["reason_codes"]

def test_evaluate_verdict_ineffective_evidence_raises_error(db_session):
    scenario = db_session.query(ScenarioModel).first()
    marina = db_session.query(SuspectModel).filter_by(name="Marina Souza", scenario_id=scenario.id).first()
    relatorio = db_session.query(EvidenceModel).filter_by(name="Relatório Contábil Alterado", scenario_id=scenario.id).first()
    
    session = SessionModel(scenario_id=scenario.id, status="in_progress")
    db_session.add(session)
    db_session.commit()
    
    # Used, but was NOT effective
    usage = SessionEvidenceUsageModel(session_id=session.id, suspect_id=marina.id, evidence_id=relatorio.id, was_effective=False)
    db_session.add(usage)
    db_session.commit()

    from app.core.exceptions import RuleViolationError
    with pytest.raises(RuleViolationError):
        evaluate_verdict(
            session_id=session.id,
            chosen_suspect_id=marina.id,
            evidence_ids=[relatorio.id],
            motive_key="financial_gain",
            db=db_session
        )

def test_evaluate_verdict_wrong_suspect_missing_evidence(db_session):
    scenario = db_session.query(ScenarioModel).first()
    # Wrong suspect
    wrong_suspect = db_session.query(SuspectModel).filter(SuspectModel.name != "Marina Souza", SuspectModel.scenario_id == scenario.id).first()
    
    session = SessionModel(scenario_id=scenario.id, status="in_progress")
    db_session.add(session)
    db_session.commit()

    verdict = evaluate_verdict(
        session_id=session.id,
        chosen_suspect_id=wrong_suspect.id,
        evidence_ids=[],
        motive_key="financial_gain",
        db=db_session
    )

    assert verdict["result_type"] == "wrong"
    assert "wrong_suspect" in verdict["reason_codes"]
