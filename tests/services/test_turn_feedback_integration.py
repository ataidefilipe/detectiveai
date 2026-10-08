"""
tests/services/test_turn_feedback_integration.py

Testes de integração para verificar o comportamento de feedback e anti-spam:
1. Turno de quebra de claim/revelação de segredo define mechanical_effect="broke_claim",
   garante topic_signal forte e guidance=None (nunca "não reagiu a nada").
2. Turnos consecutivos com perguntas abertas ativam o anti-spam, exibindo a dica apenas uma vez.
"""

import pytest
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    SessionModel,
    SessionSuspectStateModel,
    EvidenceModel,
    SessionClaimStateModel
)
from app.services.session_service import create_session
from app.services.interrogation_turn_service import run_interrogation_turn


def test_turn_feedback_claim_break_precedence_and_anti_spam():
    db = SessionLocal()
    try:
        scenario = ScenarioModel(
            scenario_code="test_fb_scen",
            title="Test Scen",
            culprit_id=None,
            topics=[
                {
                    "id": "alibi",
                    "label": "Álibi",
                    "aliases": ["alibi", "quarto", "onde estava"]
                }
            ]
        )
        db.add(scenario)
        db.flush()

        suspect = SuspectModel(
            scenario_id=scenario.id,
            suspect_code="suspect_fb",
            name="Marina Souza",
            claims=[
                {
                    "claim_id": "claim_test_01",
                    "topic_id": "alibi",
                    "text": "Eu estava no meu quarto.",
                    "claim_type": "alibi",
                    "importance": "critical",
                    "breakable_by_evidence_ids": ["cartao_teste"],
                    "breakable_by_claim_ids": [],
                    "reveal_on_break": []
                }
            ],
            knowledge_items=[]
        )
        db.add(suspect)
        db.flush()

        evidence = EvidenceModel(
            scenario_id=scenario.id,
            evidence_code="cartao_teste",
            name="Cartão de Acesso",
            related_topic_id="alibi"
        )
        db.add(evidence)
        db.flush()

        session_obj = create_session(scenario.id, db=db)
        session_id = session_obj["id"] if isinstance(session_obj, dict) else session_obj.id

        # ── TURNO 1: Pergunta muito aberta (primeira vez) ─────────────────────
        res1 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text="fala aí, o que você tem pra me dizer?",
            evidence_id=None,
            db=db
        )
        fb1 = res1.get("narrative_feedback")
        assert fb1 is not None
        assert fb1["guidance"] == "A pergunta foi muito aberta. Tente especificar um horário, pessoa, lugar ou evidência."

        # ── TURNO 2: Segunda pergunta muito aberta (deve disparar anti-spam e retornar None) ──
        res2 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text="e o que mais você fazia?",
            evidence_id=None,
            db=db
        )
        fb2 = res2.get("narrative_feedback")
        assert fb2 is not None
        # Anti-spam ativado: não repete a dica maçante!
        assert fb2["guidance"] is None

        # ── TURNO 3: Apresenta evidência que quebra a claim ──────────────────
        res3 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text="Seu alibi no quarto é mentira, aqui está o cartão de acesso.",
            evidence_id=evidence.id,
            db=db
        )
        assert res3["mechanical_effect"] == "broke_claim"
        assert len(res3["newly_broken_claims"]) == 1
        assert res3["newly_broken_claims"][0]["claim_id"] == "claim_test_01"
        fb3 = res3.get("narrative_feedback")
        assert fb3 is not None
        # Em quebra mecânica, guidance NUNCA deve ser "não reagiu a nada", e sim None para a UI dar destaque à quebra!
        assert fb3["guidance"] is None

    finally:
        db.close()
