from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.schemas.chat import PlayerChatInput

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect

router = APIRouter(prefix="/sessions")
