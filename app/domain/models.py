from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Scenario(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., description="Title of the scenario")
    description: Optional[str] = None
    culprit_id: Optional[int] = None  # ID of the guilty suspect

class Suspect(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    name: str = Field(..., description="Name of the suspect")
    backstory: Optional[str] = None

class Evidence(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    name: str = Field(..., description="Name of the evidence")
    description: Optional[str] = None

class Secret(BaseModel):
    id: Optional[int] = None
    suspect_id: int
    evidence_id: int
    content: str = Field(..., description="Secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class Session(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    status: str = Field(default="in_progress", description="Session status")
    created_at: datetime = Field(default_factory=datetime.now)

class SessionSuspectState(BaseModel):
    session_id: int
    suspect_id: int
    revealed_secret_ids: List[int] = Field(default_factory=list)
    is_closed: bool = Field(default=False)
    progress: float = Field(default=0.0)

class NpcChatMessage(BaseModel):
    id: Optional[int] = None
    session_id: int
    suspect_id: int
    sender_type: str = Field(..., description="player or npc")
    text: str = Field(..., description="Message content")
    evidence_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionEvidenceUsage(BaseModel):
    session_id: int
    suspect_id: int
    evidence_id: int
    used_at: datetime = Field(default_factory=datetime.now)
