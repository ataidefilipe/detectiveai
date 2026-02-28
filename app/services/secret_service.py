from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SecretModel,
    SessionSuspectStateModel,
    SuspectModel
)
from app.core.exceptions import NotFoundError


def apply_evidence_to_suspect(
    session_id: int,
    suspect_id: int,
    evidence_id: int,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Applies evidence to a suspect:
      - Reveals secrets associated with that evidence
      - Updates progress
      - If all core secrets are revealed, marks suspect as 'closed'
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
            return []

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
        else:
            # No core secrets → progress always 1.0
            state.progress = 1.0

        # ---------------------------------------
        # 5. If all core secrets revealed → close suspect
        # ---------------------------------------
        if total_core > 0 and state.progress == 1.0:
            state.is_closed = True

        db.flush()
        db.refresh(state)

        if close_session:
            db.commit()

        return revealed_now

    finally:
        if close_session:
            db.close()
