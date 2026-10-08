from pydantic import BaseModel
from typing import List, Optional

class CaseFileEvidenceSchema(BaseModel):
    evidence_id: int
    evidence_code: Optional[str]
    name: str
    suspect_id: int

class CaseFileClaimSchema(BaseModel):
    claim_id: str
    statement: str
    suspect_id: int
    is_broken: bool

class CaseFileFactSchema(BaseModel):
    source_type: str # 'secret', 'knowledge', 'claim'
    content: str
    suspect_id: int
    # Sprint 3 T4.3
    source_id: Optional[str] = None
    topic_id: Optional[str] = None

class MotiveClueSchema(BaseModel):
    id: str
    motive_key: str
    topic_id: str
    content: str
    revealed_by_suspect_id: int
    revealed_by_evidence_code: Optional[str]

class CaseFileSuspectSummarySchema(BaseModel):
    suspect_id: int
    name: str
    stance: str
    patience: float
    pressure: float

class CaseFileResponse(BaseModel):
    session_id: int
    confirmed_facts: List[CaseFileFactSchema]
    open_threads: List[str] # Topic IDs
    # Sprint 3 T4.2
    promising_threads: List[str] = []
    resolved_threads: List[str] = []
    effective_evidences: List[CaseFileEvidenceSchema]
    ineffective_evidences: List[CaseFileEvidenceSchema]
    claims: List[CaseFileClaimSchema]
    suspect_summaries: List[CaseFileSuspectSummarySchema]
    motive_clues: List[MotiveClueSchema]
