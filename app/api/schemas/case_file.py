from typing import List
from pydantic import BaseModel

class SecretEntry(BaseModel):
    id: int
    content: str
    is_core: bool

class KnowledgeEntry(BaseModel):
    id: str
    revealed_text: str

class BrokenLieEntry(BaseModel):
    id: str
    statement: str

class EffectiveEvidenceEntry(BaseModel):
    id: int
    name: str

class CaseFileSuspectEntry(BaseModel):
    suspect_id: int
    name: str
    revealed_secrets: List[SecretEntry]
    discovered_knowledge: List[KnowledgeEntry]
    broken_lies: List[BrokenLieEntry]
    effective_evidences: List[EffectiveEvidenceEntry]

class CaseFileResponse(BaseModel):
    session_id: int
    suspects: List[CaseFileSuspectEntry]
