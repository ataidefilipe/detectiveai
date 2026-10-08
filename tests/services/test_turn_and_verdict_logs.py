import pytest
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    TurnLogModel,
    VerdictLogModel,
)
from app.services.session_service import create_session
from app.services.interrogation_turn_service import run_interrogation_turn
from app.services.session_finalize_service import finalize_session


@pytest.fixture
def db():
    session = SessionLocal()

    scenario = ScenarioModel(
        scenario_code="test_log_case",
        title="Test Log Case",
        description="Scenario for testing logs",
        culprit_id=1,
        true_motive_key="money",
        required_evidence_ids=[1],
        required_broken_claim_ids=["claim_1"],
        motive_options=[{"key": "money", "label": "Dinheiro"}],
        motive_clues=[],
        topics=[{"id": "dinheiro", "aliases": ["dinheiro", "grana"], "is_sensitive": True}],
    )
    session.add(scenario)
    session.flush()

    suspect = SuspectModel(
        id=1,
        scenario_id=scenario.id,
        name="Suspect One",
        personality="defensivo",
        claims=[
            {
                "claim_id": "claim_1",
                "statement": "Nunca peguei dinheiro.",
                "topic_id": "dinheiro",
                "breakable_by_evidence_ids": [1],
            }
        ],
        knowledge_items=[],
        secrets=[],
    )
    session.add(suspect)

    evidence = EvidenceModel(
        id=1,
        scenario_id=scenario.id,
        name="Extrato Bancário",
        description="Extrato com transferência suspeita.",
    )
    session.add(evidence)
    session.commit()

    game_session = create_session(scenario_id=scenario.id, db=session)

    yield session, game_session["id"]

    session.close()


def test_turn_logs_persisted_on_turn(db):
    session, session_id = db
    # Turno 1
    resp1 = run_interrogation_turn(
        session_id=session_id,
        suspect_id=1,
        text="Onde está o dinheiro?",
        evidence_id=None,
        db=session,
    )
    session.commit()

    logs = session.query(TurnLogModel).filter(TurnLogModel.session_id == session_id).all()
    assert len(logs) == 1
    log1 = logs[0]

    assert log1.turn_number == 1
    assert log1.session_id == session_id
    assert log1.suspect_id == 1
    assert log1.player_text == "Onde está o dinheiro?"
    assert log1.npc_text == resp1["npc_message"]["text"]
    assert log1.state_before is not None
    assert log1.state_after is not None
    assert log1.analysis is not None
    assert log1.transition is not None
    assert log1.effects is not None
    assert log1.ai is not None
    assert log1.prompt is not None

    # Turno 2 (confrontando com evidência)
    resp2 = run_interrogation_turn(
        session_id=session_id,
        suspect_id=1,
        text="Explique esse extrato bancário!",
        evidence_id=1,
        db=session,
    )
    session.commit()

    logs = session.query(TurnLogModel).filter(TurnLogModel.session_id == session_id).order_by(TurnLogModel.turn_number.asc()).all()
    assert len(logs) == 2
    log2 = logs[1]

    assert log2.turn_number == 2
    assert log2.evidence_id == 1
    assert log2.player_text == "Explique esse extrato bancário!"


def test_verdict_logs_persisted_on_finalize(db):
    session, session_id = db
    # Registra uso efetivo da evidência e quebra da claim para veredito válido
    from app.infra.db_models import SessionEvidenceUsageModel, SessionClaimStateModel
    usage = SessionEvidenceUsageModel(
        session_id=session_id,
        suspect_id=1,
        evidence_id=1,
        was_effective=True,
        effect_type="broke_claim",
    )
    session.add(usage)
    claim_state = session.query(SessionClaimStateModel).filter(
        SessionClaimStateModel.session_id == session_id,
        SessionClaimStateModel.claim_id == "claim_1"
    ).first()
    if claim_state:
        claim_state.status = "broken"
    session.commit()

    # Finaliza a sessão
    res = finalize_session(
        session_id=session_id,
        chosen_suspect_id=1,
        evidence_ids=[1],
        motive_key="money",
        db=session,
    )

    verdict_logs = session.query(VerdictLogModel).filter(VerdictLogModel.session_id == session_id).all()
    assert len(verdict_logs) == 1
    vlog = verdict_logs[0]

    assert vlog.session_id == session_id
    assert vlog.chosen_suspect_id == 1
    assert vlog.real_culprit_id == 1
    assert vlog.result_type in ("correct", "partial", "wrong")
    assert vlog.chosen_motive_key == "money"
    assert vlog.motive_result == "correct"
    assert vlog.verdict is not None
    assert vlog.session_summary is not None
    assert vlog.session_summary["total_turns"] >= 0
