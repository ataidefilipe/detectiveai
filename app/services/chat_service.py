from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    SuspectModel,
    NpcChatMessageModel,
    SessionSuspectStateModel,
    SessionEvidenceUsageModel,
    SecretModel,
    EvidenceModel,
    EvidenceModel,
    ScenarioModel
)
from app.core.exceptions import NotFoundError, RuleViolationError

from app.services.ai_adapter_factory import get_npc_ai_adapter
from app.services.npc_context_builder import build_npc_context

ai = get_npc_ai_adapter()

def add_player_message(
    session_id: int,
    suspect_id: int,
    text: str,
    evidence_id: Optional[int] = None,
    db: Optional[Session] = None
) -> dict:
    """
    Registers a player message and returns a clean dictionary with message info.
    Prevents DetachedInstanceError by not returning ORM objects.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Validate session
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise NotFoundError(f"Session {session_id} not found.")

        if session.status == "finished":
            raise RuleViolationError(f"Session {session_id} is already finished.")

        # Validate suspect
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id,
            SuspectModel.scenario_id == session.scenario_id
        ).first()
        if not suspect:
            raise NotFoundError(f"Suspect {suspect_id} is not part of scenario {session.scenario_id}.")

        # Validate evidence
        if evidence_id is not None:
            evidence = db.query(EvidenceModel).filter(
                EvidenceModel.id == evidence_id,
                EvidenceModel.scenario_id == session.scenario_id
            ).first()

            if not evidence:
                raise NotFoundError(
                    f"Evidence {evidence_id} is not valid for scenario {session.scenario_id}."
                )

        # Create message
        msg = NpcChatMessageModel(
            session_id=session_id,
            suspect_id=suspect_id,
            sender_type="player",
            text=text,
            evidence_id=evidence_id
        )

        db.add(msg)
        db.flush()
        db.refresh(msg)

        # Log evidence usage

        if evidence_id is not None:
            existing = db.query(SessionEvidenceUsageModel).filter(
                SessionEvidenceUsageModel.session_id == session_id,
                SessionEvidenceUsageModel.suspect_id == suspect_id,
                SessionEvidenceUsageModel.evidence_id == evidence_id
            ).first()

            if not existing:
                usage = SessionEvidenceUsageModel(
                    session_id=session_id,
                    suspect_id=suspect_id,
                    evidence_id=evidence_id
                )
                db.add(usage)
                db.flush()

        if close_session:
            db.commit()

        # Convert ORM → dict before closing session
        result = {
            "id": msg.id,
            "session_id": msg.session_id,
            "suspect_id": msg.suspect_id,
            "text": msg.text,
            "sender_type": msg.sender_type,
            "evidence_id": msg.evidence_id,
            "timestamp": msg.timestamp.isoformat(),
        }

        return result

    finally:
        if close_session:
            db.close()

def add_npc_reply(
    session_id: int,
    suspect_id: int,
    player_message_id: int,
    db: Optional[Session] = None
) -> NpcChatMessageModel:
    """
    Generates an NPC reply after a player sends a message.

    Steps:
    1. Load suspect state (revealed secrets, closed flag, personality info)
    2. Load recent chat history
    3. Load the player message content
    4. Call the AI adapter to generate reply text
    5. Save NPC message to DB
    6. Return that DB object
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ----------------------------------------
        # 1. Load suspect state for this session
        # ----------------------------------------
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise NotFoundError(f"Suspect {suspect_id} not part of session {session_id}.")

        # Load suspect model (for personality, final phrase, etc.)
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id
        ).first()

        true_timeline = suspect.true_timeline or []
        lies = suspect.lies or []

        # ----------------------------------------
        # 2. Load chat history for this suspect/session
        # ----------------------------------------
        history_rows = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id
        ).order_by(NpcChatMessageModel.timestamp.asc()).all()

        chat_history = [
            {
                "sender": row.sender_type,
                "text": row.text,
                "evidence_id": row.evidence_id,
                "timestamp": row.timestamp.isoformat()
            }
            for row in history_rows
        ]

        # ----------------------------------------
        # 3. Load the player message
        # ----------------------------------------
        player_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.id == player_message_id
        ).first()

        if not player_msg:
            raise NotFoundError(f"Player message {player_message_id} not found.")

        player_message_dict = {
            "text": player_msg.text,
            "evidence_id": player_msg.evidence_id
        }

        # ----------------------------------------
        # 4. Build suspect_state for AI
        # ----------------------------------------
        revealed_secrets = []
        if state.revealed_secret_ids:
            secrets = db.query(SecretModel).filter(
                SecretModel.id.in_(state.revealed_secret_ids)
            ).all()
            for sc in secrets:
                revealed_secrets.append({
                    "secret_id": sc.id,
                    "content": sc.content,
                    "is_core": sc.is_core
                })

        # Hidden secrets (just for dummy AI)
        hidden_secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id
        ).all()

        hidden_list = [
            {"secret_id": sc.id, "content": sc.content, "is_core": sc.is_core}
            for sc in hidden_secrets
            if sc.id not in state.revealed_secret_ids
        ]

        suspect_state = {
            "suspect_id": suspect_id,
            "name": suspect.name if suspect else "O suspeito",
            "personality": suspect.backstory or "neutro",
            "revealed_secrets": revealed_secrets,
            "hidden_secrets": hidden_list,
            "is_closed": state.is_closed,
            "final_phrase": (
                suspect.final_phrase
                if suspect and suspect.final_phrase
                else "Já falei tudo que sabia."
            )
        }

        # ----------------------------------------
        # Load scenario
        # ----------------------------------------

        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == session_id)
            .first()
        )

        if not session:
            raise NotFoundError(f"Session {session_id} not found")        

        scenario = (
            db.query(ScenarioModel)
            .filter(ScenarioModel.id == session.scenario_id)
            .first()
        )

        if not scenario:
            raise NotFoundError("Scenario not found for session")

        # ----------------------------------------
        # Build pressure points (MVP)
        # ----------------------------------------
        pressure_points = [
            {
                "evidence_id": msg["evidence_id"],
                "text": msg["text"]
            }
            for msg in chat_history
            if msg.get("evidence_id") is not None
        ]

        # ----------------------------------------
        # Call AI adapter
        # ----------------------------------------
        npc_context = build_npc_context(
            scenario=scenario,
            suspect=suspect,
            suspect_state=suspect_state,
            revealed_secrets=revealed_secrets,
            pressure_points=pressure_points,
        )

        reply_text = ai.generate_reply(
            suspect_state=suspect_state,
            npc_context=npc_context,
            chat_history=chat_history,
            player_message=player_message_dict
        )

        # ----------------------------------------
        # 6. Save NPC message
        # ----------------------------------------
        npc_msg = NpcChatMessageModel(
            session_id=session_id,
            suspect_id=suspect_id,
            sender_type="npc",
            text=reply_text
        )

        db.add(npc_msg)
        db.flush()
        db.refresh(npc_msg)

        if close_session:
            db.commit()

        return {
            "id": npc_msg.id,
            "session_id": npc_msg.session_id,
            "suspect_id": npc_msg.suspect_id,
            "sender_type": npc_msg.sender_type,
            "text": npc_msg.text,
            "evidence_id": npc_msg.evidence_id,
            "timestamp": npc_msg.timestamp.isoformat()
        }

    finally:
        if close_session:
            db.close()