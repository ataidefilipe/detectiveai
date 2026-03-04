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
    sensitive_topic_ids: List[str] = Field(default_factory=list)
    intent: MessageIntent = MessageIntent.unknown
    sensitivity_hit: SensitivityLevel = SensitivityLevel.none
    novelty: NoveltyLevel = NoveltyLevel.unknown
    specificity: SpecificityLevel = SpecificityLevel.low
    confidence: float = 0.0
    notes: Optional[str] = None

class ConversationEffect(str, Enum):
    none = "none"
    new_topic = "new_topic"
    deeper_topic = "deeper_topic"
    sensitive_touch = "sensitive_touch"
    repeat = "repeat"
    out_of_context = "out_of_context"
    claim_commit = "claim_commit"
    partial_reveal = "partial_reveal"

class NpcShift(str, Enum):
    none = "none"
    more_defensive = "more_defensive"
    more_cooperative = "more_cooperative"
    pressured = "pressured"
    irritated = "irritated"

class StateTransitionResult(BaseModel):
    conversation_effect: ConversationEffect = ConversationEffect.none
    npc_shift: NpcShift = NpcShift.none
    state_deltas: dict = Field(default_factory=dict)
    debug_reason_codes: list[str] = Field(default_factory=list)

class TopicSignal(str, Enum):
    none = "none"
    weak = "weak"
    good = "good"
    strong = "strong"

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


class TurnDebugTrace(BaseModel):
    message_analysis: Optional[MessageAnalysisResult] = None
    state_transition: Optional[StateTransitionResult] = None
    allowed_knowledge: list[str] = Field(default_factory=list)
    new_knowledge_this_turn: list[str] = Field(default_factory=list)

class PlayerTurnResponse(BaseModel):
    player_message: ChatMessageInfo
    npc_message: ChatMessageInfo
    revealed_secrets: list[dict]
    evidence_effect: str  # "none" | "revealed_secret" | "duplicate" | "out_of_context"
    suspect_state: dict
    message_analysis: Optional[MessageAnalysisResult] = None
    state_transition: Optional[StateTransitionResult] = None
    
    # Systemic Discrete Feedback
    conversation_effect: str = "none"
    npc_shift: str = "none"
    topic_signal: TopicSignal = TopicSignal.none
    feedback_hints: List[str] = Field(default_factory=list)
    
    debug_trace: Optional[TurnDebugTrace] = None
