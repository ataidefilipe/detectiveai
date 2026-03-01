from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class MessageIntent(str, Enum):
    ask = "ask"
    pressure = "pressure"
    confront = "confront"
    accuse = "accuse"
    calm = "calm"
    unknown = "unknown"

class SensitivityLevel(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"

class NoveltyLevel(str, Enum):
    new = "new"
    repeat = "repeat"
    reframe = "reframe"
    unknown = "unknown"

class SpecificityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class MessageAnalysisResult(BaseModel):
    primary_topic_id: Optional[str] = None
    detected_topic_ids: List[str] = Field(default_factory=list)
    intent: MessageIntent = MessageIntent.unknown
    sensitivity_hit: SensitivityLevel = SensitivityLevel.none
    novelty: NoveltyLevel = NoveltyLevel.unknown
    specificity: SpecificityLevel = SpecificityLevel.low
    confidence: float = 0.0
    notes: Optional[str] = None

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
    message_analysis: Optional[MessageAnalysisResult] = None
