import pytest
from app.services.secret_service import apply_evidence_to_suspect
from app.infra.db_models import (
    ScenarioModel, SuspectModel, EvidenceModel, SecretModel, SessionModel, SessionSuspectStateModel
)
from app.api.schemas.chat import ConversationMemory
from tests.conftest import TestingSessionLocal

@pytest.fixture
def evidence_scenario_db():
    db = TestingSessionLocal()
    
    # 1. Setup scenario
    scenario = ScenarioModel(scenario_code="ctxt1", title="E1 Test Scenario", culprit_id=999)
    db.add(scenario)
    db.flush()
    
    # 2. Setup suspect
    suspect = SuspectModel(scenario_id=scenario.id, name="Test Suspect")
    db.add(suspect)
    db.flush()
    
    # 3. Setup evidences
    ev_contextual = EvidenceModel(
        scenario_id=scenario.id, name="Contextual Evidence", description="Needs topic", related_topic_id="weapon"
    )
    ev_free = EvidenceModel(
        scenario_id=scenario.id, name="Free Evidence", description="No topic needed", related_topic_id=None
    )
    db.add_all([ev_contextual, ev_free])
    db.flush()
    
    # 4. Setup Secrets
    sec1 = SecretModel(
        suspect_id=suspect.id, evidence_id=ev_contextual.id, content="Secret 1", is_core=True
    )
    sec2 = SecretModel(
        suspect_id=suspect.id, evidence_id=ev_contextual.id, content="Secret 2", is_core=False
    )
    sec3 = SecretModel(
        suspect_id=suspect.id, evidence_id=ev_free.id, content="Secret 3", is_core=True
    )
    db.add_all([sec1, sec2, sec3])
    db.flush()

    # 5. Setup session and state
    session = SessionModel(scenario_id=scenario.id)
    db.add(session)
    db.flush()
    
    suspect_state = SessionSuspectStateModel(
        session_id=session.id, suspect_id=suspect.id,
        stance="neutral", patience=50.0, pressure=50.0, rapport=50.0, progress=0.0
    )
    db.add(suspect_state)
    db.commit()
    
    yield {
        "db": db,
        "session_id": session.id,
        "suspect_id": suspect.id,
        "ev_contextual_id": ev_contextual.id,
        "ev_free_id": ev_free.id
    }
    
    db.close()


def test_evidence_out_of_context_blocked(evidence_scenario_db):
    db = evidence_scenario_db["db"]
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["weather", "gossip"], # Wrong topics
        db=db
    )
    
    assert effect == "out_of_context"
    assert len(revealed) == 0

def test_evidence_contextual_accepted(evidence_scenario_db):
    db = evidence_scenario_db["db"]
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["alibi", "weapon"], # Correct topic "weapon" is present
        db=db
    )
    
    assert effect == "revealed_secret"
    assert len(revealed) == 2

def test_evidence_free_accepted(evidence_scenario_db):
    db = evidence_scenario_db["db"]
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_free_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["irrelevant"], # Topic doesn't matter for this evidence
        db=db
    )
    
    assert effect == "revealed_secret"
    assert len(revealed) == 1

def test_evidence_out_of_context_high_pressure_still_blocked(evidence_scenario_db):
    db = evidence_scenario_db["db"]
    
    # Set high pressure
    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == evidence_scenario_db["session_id"]
    ).first()
    state.pressure = 85.0
    db.commit()
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["wrong"], 
        db=db
    )
    
    # T8: High pressure no longer bypasses the context wall
    assert effect == "out_of_context"
    assert len(revealed) == 0

def test_evidence_short_term_context_accepted(evidence_scenario_db):
    db = evidence_scenario_db["db"]
    
    # Simulating that "weapon" was the primary topic in a previous turn
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=["weapon"], active_topic_id="weapon", last_topic_id="weapon", recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=True),
        detected_topics=[], # No explicit topic detected this turn
        db=db
    )
    
    # T6/T7: The evidence is accepted based on the short-term context history
    assert effect == "revealed_secret"
    assert len(revealed) == 2


# ── T2.1: Semantic Evidence Context ──────────────────────────────────────────

def test_evidence_referenced_by_gpt_is_accepted(evidence_scenario_db):
    """Caso NOVO 1: evidence_id em referenced_evidence_ids → True (válida)"""
    db = evidence_scenario_db["db"]
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["wrong"], 
        referenced_evidence_ids=[evidence_scenario_db["ev_contextual_id"]],
        db=db
    )
    
    assert effect == "revealed_secret"
    assert len(revealed) == 2


def test_evidence_targeting_claim_is_accepted(evidence_scenario_db):
    """Caso NOVO 2: evidence_code quebra claim alvo → True (válida)"""
    db = evidence_scenario_db["db"]
    
    # Adicionar uma claim ao suspeito
    suspect = db.query(SuspectModel).filter(SuspectModel.id == evidence_scenario_db["suspect_id"]).first()
    ev_contextual = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_scenario_db["ev_contextual_id"]).first()
    ev_contextual.evidence_code = "weapon_code_01"
    
    suspect.claims = [{
        "claim_id": "claim_no_weapon",
        "topic_id": "weapon",
        "text": "Não uso armas",
        "breakable_by_evidence_codes": ["weapon_code_01"]
    }]
    db.commit()
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["wrong"], 
        target_claim_ids=["claim_no_weapon"],
        db=db
    )
    
    assert effect == "revealed_secret"


def test_target_claim_ids_without_match_is_blocked(evidence_scenario_db):
    """Caso NOVO 4: target_claim_ids sem match de evidence_code → False"""
    db = evidence_scenario_db["db"]
    
    suspect = db.query(SuspectModel).filter(SuspectModel.id == evidence_scenario_db["suspect_id"]).first()
    ev_contextual = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_scenario_db["ev_contextual_id"]).first()
    ev_contextual.evidence_code = "weapon_code_01"
    
    suspect.claims = [{
        "claim_id": "claim_no_weapon",
        "topic_id": "weapon",
        "text": "Não uso armas",
        "breakable_by_evidence_codes": ["other_evidence_code"]
    }]
    db.commit()
    
    revealed, effect = apply_evidence_to_suspect(
        session_id=evidence_scenario_db["session_id"],
        suspect_id=evidence_scenario_db["suspect_id"],
        evidence_id=evidence_scenario_db["ev_contextual_id"],
        conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
        detected_topics=["wrong"], 
        target_claim_ids=["claim_no_weapon"],
        db=db
    )
    
    assert effect == "out_of_context"
