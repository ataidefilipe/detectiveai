from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class TurnLogItemSchema(BaseModel):
    id: int
    session_id: int
    suspect_id: int
    turn_number: int
    created_at: str

    player_message_id: Optional[int] = None
    npc_message_id: Optional[int] = None
    player_text: str
    npc_text: Optional[str] = None
    evidence_id: Optional[int] = None

    intent: Optional[str] = None
    move_type: Optional[str] = None
    primary_topic_id: Optional[str] = None
    analysis_provider: Optional[str] = None
    evidence_effect: Optional[str] = None
    response_mode: Optional[str] = None

    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    transition: Optional[Dict[str, Any]] = None
    effects: Optional[Dict[str, Any]] = None
    ai: Optional[Dict[str, Any]] = None
    prompt: Optional[Any] = None


class SessionTurnsLogResponse(BaseModel):
    session_id: int
    total_turns: int
    turns: List[TurnLogItemSchema]


class VerdictLogResponse(BaseModel):
    id: int
    session_id: int
    scenario_id: int
    created_at: str
    result_type: str
    chosen_suspect_id: int
    real_culprit_id: Optional[int] = None
    chosen_motive_key: Optional[str] = None
    motive_result: Optional[str] = None
    evidence_ids: List[int] = Field(default_factory=list)
    verdict: Optional[Dict[str, Any]] = None
    session_summary: Optional[Dict[str, Any]] = None
