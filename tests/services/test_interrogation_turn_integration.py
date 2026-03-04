import pytest
from app.infra.db_models import (
    SessionModel, SuspectModel, SecretModel, EvidenceModel,
    ScenarioModel, SessionSuspectStateModel, NpcChatMessageModel,
    SessionSuspectTopicStateModel
)
from app.services.interrogation_turn_service import run_interrogation_turn
from app.api.schemas.chat import ConversationEffect, TopicSignal
from app.infra.db import SessionLocal, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from unittest.mock import patch

# Set up an in-memory SQLite database for integration testing
@pytest.fixture(autouse=True)
def enable_debug_trace():
    with patch("app.services.interrogation_turn_service.settings") as mock_settings:
        mock_settings.DEBUG_TURN_TRACE = True
        yield

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # 1. Setup Base Scenario Data
    # Topics mock (in DB it is stored as JSON in scenario.topics usually)
    topics = [
        {"id": "faca", "aliases": ["arma", "faca"], "is_sensitive": True},
        {"id": "local", "aliases": ["onde", "cidade"], "is_sensitive": False}
    ]
    
    scenario = ScenarioModel(id=1, title="Test Scenario", description="A test scenario", topics=topics)
    db.add(scenario)
    
    # Suspect
    suspect = SuspectModel(
        id=1, 
        scenario_id=1, 
        name="John Doe", 
        personality="nervoso",
        knowledge_items=[
             {
                 "id": "faca_detail",
                 "topic_id": "faca",
                 "content_layers": ["A faca estava no chão.", "A faca tinha minhas digitais."]
             }
        ]
    )
    db.add(suspect)
    
    # Session
    session = SessionModel(id=1, scenario_id=1)
    db.add(session)
    
    # Session Suspect State
    state = SessionSuspectStateModel(session_id=1, suspect_id=1, stance="neutral", patience=100.0, pressure=0.0)
    db.add(state)
    
    # Session Suspect Topic State
    topic_state1 = SessionSuspectTopicStateModel(session_id=1, suspect_id=1, topic_id="faca")
    topic_state2 = SessionSuspectTopicStateModel(session_id=1, suspect_id=1, topic_id="local")
    db.add_all([topic_state1, topic_state2])
    
    # Evidence
    evi1 = EvidenceModel(id=1, scenario_id=1, name="Faca Suja", description="Uma faca de cozinha", related_topic_id="faca")
    evi2 = EvidenceModel(id=2, scenario_id=1, name="Chave do Carro", description="Chaves soltas", related_topic_id="carro")
    db.add_all([evi1, evi2])
    
    # Secrets
    secret1 = SecretModel(id=1, suspect_id=1, content="Eu usei a faca", is_core=True, evidence_id=1)
    db.add(secret1)
    
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_integration_vague_question_weak_signal(db_session):
    res = run_interrogation_turn(session_id=1, suspect_id=1, text="Hmm, qual é mesmo a sua cor favorita?", evidence_id=None, db=db_session)
    
    assert res["topic_signal"] == TopicSignal.weak
    assert "pergunta muito vaga" in res["feedback_hints"]
    assert res["evidence_effect"] == "none"
    assert res["conversation_effect"] == "none"

def test_integration_sensitive_topic_touch(db_session):
    # Faca is marked is_sensitive=True
    res = run_interrogation_turn(session_id=1, suspect_id=1, text="Me fale sobre a faca.", evidence_id=None, db=db_session)
    
    # Heuristic: Sensitive topic without much pressure often drops patience.
    # We should see the topic in the analysis and the topic signal reflecting it.
    assert "faca" in res["message_analysis"].detected_topic_ids
    assert "faca" in res["message_analysis"].sensitive_topic_ids
    assert res["message_analysis"].sensitivity_hit.value == "high"
    
def test_integration_repetition_novelty(db_session):
    # First turn
    run_interrogation_turn(session_id=1, suspect_id=1, text="onde você mora na cidade?", evidence_id=None, db=db_session)
    
    # Second turn - repeat
    res = run_interrogation_turn(session_id=1, suspect_id=1, text="onde você mora na cidade?", evidence_id=None, db=db_session)
    
    assert res["message_analysis"].novelty.value == "repeat"
    assert "penalized_for_repetition" in res["state_transition"].debug_reason_codes

def test_integration_evidence_out_of_context(db_session):
    # Chave do carro doesn't unlock any secrets for "faca" context
    res = run_interrogation_turn(session_id=1, suspect_id=1, text="Esta faca tem a ver com isso?", evidence_id=2, db=db_session)
    
    assert res["evidence_effect"] == "out_of_context"
    assert "evidência fora de contexto" in res["feedback_hints"]

def test_integration_evidence_reveals_secret(db_session):
    # Presenting the Faca should reveal the secret linked to it.
    res = run_interrogation_turn(session_id=1, suspect_id=1, text="Eu encontrei a faca.", evidence_id=1, db=db_session)
    
    assert res["evidence_effect"] == "revealed_secret"
    assert len(res["revealed_secrets"]) == 1
    assert res["revealed_secrets"][0]["content"] == "Eu usei a faca"
    # Ensure Dummy adapter responded correctly. Since revealing the ONLY core secret closes the suspect,
    assert "Já falei tudo que sabia" in res["npc_message"]["text"]

from unittest.mock import patch

def test_integration_knowledge_progression(db_session):
    with patch("app.services.interrogation_turn_service.settings") as mock_settings:
        mock_settings.DEBUG_TURN_TRACE = True
        
        # Turn 1: asks about faca
        res1 = run_interrogation_turn(session_id=1, suspect_id=1, text="O que sabe sobre a faca?", evidence_id=None, db=db_session)
        
        print(f"Res1 Trace: {res1['debug_trace']}")
        
        # In the first touch, depth evaluates to 1
        assert len(res1["debug_trace"].allowed_knowledge) == 0
        assert "A faca estava no chão." in res1["debug_trace"].new_knowledge_this_turn
        
        # Turn 2: asks again. Times touched = 2. Pressure is updated.
        res2 = run_interrogation_turn(session_id=1, suspect_id=1, text="E a faca de novo?", evidence_id=None, db=db_session)
        
        # Now "A faca estava no chão." should have moved to allowed_knowledge.
        assert "A faca estava no chão." in res2["debug_trace"].allowed_knowledge
        
        # Depending on evaluate_reveal_layer(), either a new layer unlocks or we get 0 new knowledge.
        # It's highly likely times_touched=1 vs times_touched=2 bumps depth, but either way it shouldn't repeat the first one in `new_knowledge_this_turn`.
        assert "A faca estava no chão." not in res2["debug_trace"].new_knowledge_this_turn
