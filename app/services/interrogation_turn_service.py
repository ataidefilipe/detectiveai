from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_service import get_suspect_state
from app.infra.db_models import SessionEvidenceUsageModel


def run_interrogation_turn(
    session_id: int,
    suspect_id: int,
    text: str,
    evidence_id: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Orchestrates a full interrogation turn in a transactional manner.
    Expects an active database session and does not commit it.
    """

    # 1. Player message
    player_msg = add_player_message(
        session_id=session_id,
        suspect_id=suspect_id,
        text=text,
        evidence_id=evidence_id,
        db=db
    )

    # 2. Evidence logic (may reveal secrets)
    revealed_secrets = []
    if evidence_id is not None:
        revealed_secrets = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=evidence_id,
            db=db
        )

        # Log evidence usage and update was_effective if applicable
        usage = db.query(SessionEvidenceUsageModel).filter(
            SessionEvidenceUsageModel.session_id == session_id,
            SessionEvidenceUsageModel.suspect_id == suspect_id,
            SessionEvidenceUsageModel.evidence_id == evidence_id
        ).first()

        is_effective = len(revealed_secrets) > 0

        if not usage:
            usage = SessionEvidenceUsageModel(
                session_id=session_id,
                suspect_id=suspect_id,
                evidence_id=evidence_id,
                was_effective=is_effective
            )
            db.add(usage)
        else:
            if is_effective and not usage.was_effective:
                usage.was_effective = True
        
        db.flush()

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"],
        revealed_now=revealed_secrets,
        db=db
    )

    # 4. Fetch updated suspect state (snapshot for UX)
    suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )

    # Calculate evidence effect for UI feedback
    evidence_effect = "none"
    if evidence_id is not None:
        if is_effective:
            evidence_effect = "revealed_secret"
        elif usage and usage.was_effective:
            evidence_effect = "duplicate"

    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "evidence_effect": evidence_effect,
        "suspect_state": suspect_state
    }
