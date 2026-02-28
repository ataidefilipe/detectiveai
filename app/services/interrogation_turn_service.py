from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_service import get_suspect_state


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

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"],
        db=db
    )

    # 4. Fetch updated suspect state (snapshot for UX)
    suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id,
        db=db
    )

    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "suspect_state": suspect_state
    }
