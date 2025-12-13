from pydantic import BaseModel
from typing import List


class AccuseRequest(BaseModel):
    suspect_id: int
    evidence_ids: List[int]


class AccuseResponse(BaseModel):
    session_id: int
    status: str
    result_type: str
    chosen_suspect_id: int
    real_culprit_id: int
    required_evidence_ids: List[int]
    missing_evidence_ids: List[int]
    description: str
