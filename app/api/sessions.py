from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from app.services.session_service import create_session, get_session_overview
from app.api.schemas.chat import PlayerChatInput
from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect

from app.infra.db import SessionLocal
from app.infra.db_models import NpcChatMessageModel, SessionModel, SuspectModel

router = APIRouter()


# -----------------------------
# Request schema
# -----------------------------
class CreateSessionRequest(BaseModel):
    scenario_id: int


# -----------------------------
# Response schema
# -----------------------------
class CreateSessionResponse(BaseModel):
    session_id: int
    scenario_id: int
    status: str


# -----------------------------
# POST /sessions
# -----------------------------
@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(payload: CreateSessionRequest):
    try:
        session = create_session(payload.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateSessionResponse(
        session_id=session.id,
        scenario_id=session.scenario_id,
        status=session.status
    )

@router.post("/sessions/{session_id}/suspects/{suspect_id}/messages")
def send_message_to_suspect(session_id: int, suspect_id: int, payload: PlayerChatInput):
    """
    Handles a full interrogation turn:
    - save player message
    - apply evidence (if any)
    - generate NPC reply
    - return everything combined
    """

    # 1. Player message
    player_msg = add_player_message(
        session_id=session_id,
        suspect_id=suspect_id,
        text=payload.text,
        evidence_id=payload.evidence_id
    )

    # 2. Evidence logic (may reveal secrets)
    revealed_secrets = []
    if payload.evidence_id is not None:
        revealed_secrets = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=payload.evidence_id
        )

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"]
    )

    # 4. Output combined
    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets
    }


# -----------------------------
# NEW: GET /sessions/{session_id}
# -----------------------------

class SessionOverviewResponse(BaseModel):
    session: dict
    scenario: dict
    suspects: list


@router.get("/sessions/{session_id}", response_model=SessionOverviewResponse)
def api_get_session_overview(session_id: int):
    try:
        overview = get_session_overview(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return overview

class ChatMessageResponse(BaseModel):
    id: int
    sender_type: str
    text: str
    evidence_id: int | None
    timestamp: str


@router.get("/sessions/{session_id}/suspects/{suspect_id}/messages",
            response_model=List[ChatMessageResponse])
def get_chat_messages(session_id: int, suspect_id: int):
    """
    Returns the chronological chat history between the player and the suspect
    in the given session.
    """

    db = SessionLocal()

    try:
        # 1. Ensure session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

        # 2. Ensure suspect belongs to scenario of the session
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id,
            SuspectModel.scenario_id == session.scenario_id
        ).first()

        if not suspect:
            raise HTTPException(
                status_code=404,
                detail=f"Suspect {suspect_id} not found in scenario {session.scenario_id}."
            )

        # 3. Load chronological chat history
        messages = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id
        ).order_by(NpcChatMessageModel.timestamp.asc()).all()

        # 4. Serialize for output
        result = [
            ChatMessageResponse(
                id=m.id,
                sender_type=m.sender_type,
                text=m.text,
                evidence_id=m.evidence_id,
                timestamp=m.timestamp.isoformat()
            )
            for m in messages
        ]

        return result

    finally:
        db.close()