from pydantic import BaseModel
from typing import Optional

class PlayerChatInput(BaseModel):
    text: str
    evidence_id: Optional[int] = None


class ChatMessageInfo(BaseModel):
    id: int
    session_id: int
    suspect_id: int
    sender_type: str
    text: str
    evidence_id: Optional[int] = None
    timestamp: str


class PlayerTurnResponse(BaseModel):
    player_message: ChatMessageInfo
    npc_message: ChatMessageInfo
    revealed_secrets: list[dict]
    evidence_effect: str  # "none" | "revealed_secret" | "duplicate"
    suspect_state: dict
