from typing import List, Optional
from pydantic import BaseModel, Field

class SecretConfig(BaseModel):
    suspect: str = Field(..., description="Name of the suspect this secret belongs to")
    evidence: str = Field(..., description="Name of the evidence that reveals this secret")
    content: str = Field(..., description="The secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class SuspectConfig(BaseModel):
    name: str = Field(..., description="Name of the suspect")
    backstory: Optional[str] = None
    final_phrase: Optional[str] = Field(
        default="Já falei tudo que sabia.",
        description="Phrase used when the suspect is closed"
    )
class EvidenceConfig(BaseModel):
    name: str = Field(..., description="Name of the evidence")
    description: Optional[str] = None
    is_mandatory: bool = Field(default=False, description="Whether this evidence is required for correct verdict")

class ChronologyEvent(BaseModel):
    time: str = Field(..., description="Timestamp or description of the event time")
    description: str = Field(..., description="Description of the event")

class ScenarioConfig(BaseModel):
    title: str = Field(..., description="Title of the scenario")
    description: Optional[str] = None
    culprit: str = Field(..., description="Name of the guilty suspect")
    suspects: List[SuspectConfig] = Field(..., description="List of suspects")
    evidences: List[EvidenceConfig] = Field(..., description="List of evidences")
    secrets: List[SecretConfig] = Field(..., description="List of secrets")
    chronology: Optional[List[ChronologyEvent]] = None
