"""
Monta o contexto público para o classificador semântico.
NUNCA inclui: culpado real, case_summary, true_motive_key, segredos ocultos,
timeline verdadeira, internal_note.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.api.schemas.chat import ConversationMemory
from app.infra.db_models import (
    SuspectModel, ScenarioModel, EvidenceModel,
    SessionSuspectStateModel, SessionClaimStateModel
)


def build_semantic_analysis_context(
    session_id: int,
    suspect_id: int,
    scenario: ScenarioModel,
    suspect: SuspectModel,
    conversation_memory: ConversationMemory,
    db: Session,
) -> dict:
    """
    Retorna dados públicos para alimentar o classificador semântico.
    """
    # Topics (público)
    topics = scenario.topics or []

    # Claims públicas: reveladas ou já quebradas
    public_claims = []
    if suspect.claims:
        claim_states = db.query(SessionClaimStateModel).filter(
            SessionClaimStateModel.session_id == session_id,
            SessionClaimStateModel.suspect_id == suspect_id,
        ).all()
        claim_state_map = {cs.claim_id: cs for cs in claim_states}

        for c in suspect.claims:
            cid = c.get("claim_id")
            cs = claim_state_map.get(cid)
            # Incluir se revelada (dita pelo NPC) ou quebrada (conhecida pelo jogador)
            if cs and (cs.is_revealed or cs.status == "broken"):
                public_claims.append({
                    "claim_id": cid,
                    "topic_id": c.get("topic_id"),
                    "text": c.get("text", c.get("statement", "")),
                    "status": cs.status,
                })

    # Evidências públicas (id, code, name, description, related_topic_id)
    evidences = db.query(EvidenceModel).filter(
        EvidenceModel.scenario_id == scenario.id
    ).all()
    public_evidences = [
        {
            "id": e.id,
            "evidence_code": e.evidence_code,
            "name": e.name,
            "description": e.description,
            "related_topic_id": e.related_topic_id,
        }
        for e in evidences
    ]

    # Suspect state (apenas campos públicos de gameplay)
    state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id,
        SessionSuspectStateModel.suspect_id == suspect_id,
    ).first()

    suspect_state = {}
    if state:
        suspect_state = {
            "stance": state.stance,
            "patience": state.patience,
            "pressure": state.pressure,
            "rapport": state.rapport,
            "progress": state.progress,
            "is_closed": state.is_closed,
        }

    return {
        "topics": topics,
        "public_claims": public_claims,
        "public_evidences": public_evidences,
        "suspect_state": suspect_state,
        "active_topic_id": conversation_memory.active_topic_id,
        "recent_topic_ids": conversation_memory.recent_topic_ids,
        "recent_evidence_ids": conversation_memory.recent_evidence_ids,
        "recent_claim_ids": conversation_memory.recent_claim_ids,
    }
