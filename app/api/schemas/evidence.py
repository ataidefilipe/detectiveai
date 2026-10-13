from pydantic import BaseModel
from typing import Optional, List


class EvidenceUsageDetailSchema(BaseModel):
    suspect_id: int
    suspect_name: str
    was_effective: bool = False
    effect_type: Optional[str] = None
    times_presented: int = 1
    last_used_at: Optional[str] = None


class EvidenceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    evidence_code: Optional[str] = None
    image_url: Optional[str] = None
    is_used: bool = False
    usages: List[EvidenceUsageDetailSchema] = []
