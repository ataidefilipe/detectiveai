from pydantic import BaseModel
from typing import Optional, List


class UsedEvidenceItem(BaseModel):
    evidence_id: int
    name: str
    description: Optional[str] = None
    was_effective: bool = False
    effect_type: Optional[str] = None
    times_presented: int = 1
    last_used_at: Optional[str] = None


class SuspectStateSchema(BaseModel):
    stance: str = "neutral"
    patience: float = 50.0
    pressure: float = 0.0
    is_closed: bool = False
    progress: float = 0.0


class SuspectSessionResponse(BaseModel):
    suspect_id: int
    name: str
    role_title: Optional[str] = None
    image_url: Optional[str] = None
    backstory: Optional[str] = None
    initial_statement: Optional[str] = None
    personality: Optional[str] = None
    state: Optional[SuspectStateSchema] = None
    used_evidences: List[UsedEvidenceItem] = []
