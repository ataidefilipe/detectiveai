from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SecretModel,
    SessionSuspectStateModel,
    SuspectModel
)


def apply_evidence_to_suspect(
    session_id: int,
    suspect_id: int,
    evidence_id: int,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Applies an evidence to a suspect during a session.
    Reveals the secrets associated with that evidence.
    Returns a list of revealed secrets (as dictionaries).
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ---------------------------------------
        # 1. Encontrar o state do suspeito na sessão
        # ---------------------------------------
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(f"Suspect {suspect_id} not part of session {session_id}.")

        # ---------------------------------------
        # 2. Buscar segredos desse suspeito ligados à evidência
        # ---------------------------------------
        secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.evidence_id == evidence_id
        ).all()

        if not secrets:
            return []  # Nenhum segredo é revelado por essa evidência

        revealed_now = []

        # ---------------------------------------
        # 3. Revelar segredos (evitando duplicações)
        # ---------------------------------------
        for secret in secrets:
            if secret.id not in state.revealed_secret_ids:
                state.revealed_secret_ids.append(secret.id)
                revealed_now.append({
                    "secret_id": secret.id,
                    "content": secret.content,
                    "is_core": secret.is_core
                })

        # Atualizar progresso simples (quantidade revelada / total)
        total_secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id
        ).count()

        if total_secrets > 0:
            state.progress = len(state.revealed_secret_ids) / total_secrets

        db.commit()
        db.refresh(state)

        return revealed_now

    finally:
        if close_session:
            db.close()
