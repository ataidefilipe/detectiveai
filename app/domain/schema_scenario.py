from typing import List, Optional
from pydantic import BaseModel, Field

class SecretConfig(BaseModel):
    suspect: str = Field(..., description="Name of the suspect this secret belongs to")
    evidence: str = Field(..., description="Name of the evidence that reveals this secret")
    content: str = Field(..., description="The secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class SuspectConfig(BaseModel):
    name: str
    backstory: Optional[str] = None
    initial_statement: Optional[str] = Field(
        default=None,
        description="Initial statement shown to the player before interrogation"
    )
    true_timeline: Optional[list[str]] = Field(
        default=None,
        description="Linha do tempo real do suspeito (conhecimento interno do NPC)"
    )
    final_phrase: Optional[str] = Field(
        default="I've told you everything I know."
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

    case_summary: Optional[str] = Field(
        default=None,
        description="Resumo interno do caso, conhecido pelo NPC mas não exposto ao jogador"
    )
    
    culprit: str = Field(..., description="Name of the guilty suspect")
    suspects: List[SuspectConfig] = Field(..., description="List of suspects")
    evidences: List[EvidenceConfig] = Field(..., description="List of evidences")
    secrets: List[SecretConfig] = Field(..., description="List of secrets")
    chronology: Optional[List[ChronologyEvent]] = None
