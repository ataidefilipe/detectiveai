from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SecretModel,
    SessionSuspectStateModel,
    SuspectModel,
    EvidenceModel
)
from app.core.exceptions import NotFoundError


def apply_evidence_to_suspect(
    session_id: int,
    suspect_id: int,
    evidence_id: int,
    detected_topics: Optional[List[str]] = None,
    db: Optional[Session] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Applies evidence to a suspect:
      - Validates if the evidence matches the current context (out_of_context check)
      - Reveals secrets associated with that evidence
      - Updates progress
      - If all core secrets are revealed, marks suspect as 'closed'
    Returns: (revealed_now_list, evidence_effect_string)
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ---------------------------------------
        # 1. Fetch state of suspect in this session
        # ---------------------------------------
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise NotFoundError(f"Suspect {suspect_id} not part of session {session_id}.")

        # ---------------------------------------
        # 2. Find secrets revealed by this evidence
        # ---------------------------------------
        secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.evidence_id == evidence_id
        ).all()

        if not secrets:
            return [], "none"

        # ---------------------------------------
        # Context validation for E1
        # ---------------------------------------
        evidence = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
        is_context_valid = True
        
        if evidence and evidence.related_topic_id:
            msg_topics = detected_topics or []
            if evidence.related_topic_id not in msg_topics:
                # Se a evidência exige um tópico e esse tópico não está na conversa atual,
                # e a pressão do suspeito não for absurdamente alta (fallback), é fora de contexto.
                if state.pressure < 80.0:
                    is_context_valid = False

        if not is_context_valid:
            return [], "out_of_context"

        revealed_now = []

        # ---------------------------------------
        # 3. Reveal secrets (append only new ones)
        # ---------------------------------------
        for secret in secrets:
            if secret.id not in state.revealed_secret_ids:
                state.revealed_secret_ids.append(secret.id)
                revealed_now.append({
                    "secret_id": secret.id,
                    "content": secret.content,
                    "is_core": secret.is_core
                })

        # ---------------------------------------
        # 4. Recalculate progress (core secrets only)
        # ---------------------------------------
        all_core = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.is_core == True
        ).all()

        total_core = len(all_core)

        if total_core > 0:
            revealed_core = sum(
                1 for s in all_core if s.id in state.revealed_secret_ids
            )
            state.progress = revealed_core / total_core
            
            if state.progress >= 1.0:
                state.is_closed = True
        else:
            # ---------------------------------------
            # Fallback for Suspects without Core Secrets
            # ---------------------------------------
            all_regular = db.query(SecretModel).filter(
                SecretModel.suspect_id == suspect_id,
            ).all()
            
            total_regular = len(all_regular)
            
            if total_regular > 0:
                revealed_regular = sum(
                    1 for s in all_regular if s.id in state.revealed_secret_ids
                )
                state.progress = revealed_regular / total_regular
                
                # Suspect without core secrets closes when all minor secrets are found
                if state.progress >= 1.0:
                    state.is_closed = True
            else:
                # No secrets at all = purely narrative NPC
                state.progress = 1.0
                state.is_closed = True

        db.flush()
        db.refresh(state)

        if close_session:
            db.commit()

        # Se não há novos segredos, mas chegamos até aqui, é duplicate. Se há, é revealed_secret.
        effect = "revealed_secret" if revealed_now else "duplicate"
        return revealed_now, effect

    finally:
        if close_session:
            db.close()
