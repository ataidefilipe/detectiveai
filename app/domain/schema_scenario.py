from typing import List, Optional
from pydantic import BaseModel, Field

class MotivationConfig(BaseModel):
    key: str = Field(..., description="Stable unique key for the motivation (e.g., 'financial_gain')")
    label: str = Field(..., description="Public label shown to the player")
    description: Optional[str] = Field(default=None, description="Internal description for the author")

class TopicConfig(BaseModel):
    id: str = Field(..., description="Unique slug for the topic, e.g., 'knife', 'victim_relationship'")
    label: str = Field(..., description="Human-readable label for the UI")
    aliases: List[str] = Field(default_factory=list, description="Synonyms, keywords, or phrases related to this topic")
    is_sensitive: bool = Field(default=False, description="Whether this topic is a sensitive touch point")
    description: Optional[str] = Field(default=None, description="Internal description of the topic")
    priority: int = Field(default=0, description="Priority weight for conflict resolution")

class KnowledgeItemConfig(BaseModel):
    id: str = Field(..., description="Unique identifier for this knowledge item")
    topic_id: str = Field(..., description="The slug of the Topic it relates to")
    kind: str = Field(default="observed", description="Enum: observed, heard, inferred, rumor, lie")
    reliability: str = Field(default="high", description="Enum: high, medium, low")
    content_layers: List[str] = Field(..., description="List of facts/phrases revealed gradually")

class SecretConfig(BaseModel):
    suspect: str = Field(..., description="Stable id of the suspect this secret belongs to")
    evidence: str = Field(..., description="Stable id of the evidence that reveals this secret")
    content: str = Field(..., description="The secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class ClaimConfig(BaseModel):
    claim_id: str = Field(..., description="Unique string identifier for the claim")
    topic_id: str = Field(..., description="The slug of the Topic it relates to")
    text: str = Field(..., description="The textual statement of the claim")
    claim_type: str = Field(..., description="Enum: alibi, relationship, timeline, denial, motive, object, location")
    importance: str = Field(default="medium", description="Enum: low, medium, high, critical")
    breakable_by_evidence_codes: List[str] = Field(
        default_factory=list,
        description="Evidence codes that can break this claim",
        alias="breakable_by_evidence_ids"
    )
    breakable_by_claim_ids: List[str] = Field(default_factory=list, description="IDs of other claims that contradict this one")
    reveal_on_break: List[str] = Field(default_factory=list, description="IDs of knowledge or secrets to reveal when broken")



class RevealedByConfig(BaseModel):
    suspect_id: Optional[str] = Field(default=None, description="Suspect ID that reveals this clue")
    evidence_code: Optional[str] = Field(default=None, description="Evidence code that reveals this clue")

class MotiveClueConfig(BaseModel):
    id: str = Field(..., description="Unique string identifier for the motive clue")
    motive_key: str = Field(..., description="Key of the motivation it hints at")
    topic_id: str = Field(..., description="The slug of the Topic it relates to")
    revealed_by: RevealedByConfig = Field(..., description="Condition to reveal this clue")
    content: str = Field(..., description="Text of the clue")

class SpeechProfile(BaseModel):
    base_verbosity: float = Field(default=0.5, ge=0.0, le=1.0, description="Extensão habitual da fala (0.0 conciso/lacônico, 1.0 muito falante)")
    stress_verbosity_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Direção e intensidade da mudança sob pressão (-1.0 fecha a boca, +1.0 fala demais/desespera-se)")

class TopicAffinityProfile(BaseModel):
    pressure_tolerance: float = Field(default=0.5, description="How well the suspect handles pressure (0.0 to 1.0)")
    empathy_receptivity: float = Field(default=0.5, description="How well the suspect responds to calm approaches (0.0 to 1.0)")
    repetition_irritability: float = Field(default=0.5, description="How easily the suspect gets annoyed by repeats (0.0 to 1.0)")
    contradiction_fragility: float = Field(default=0.5, description="How quickly the suspect breaks when contradicted (0.0 to 1.0)")
    speech: SpeechProfile = Field(default_factory=SpeechProfile, description="Perfil de verbosidade e ritmo do personagem")

class SuspectConfig(BaseModel):
    id: str = Field(..., description="Stable string identifier for the suspect")
    name: str
    backstory: Optional[str] = None
    personality: Optional[str] = None
    internal_note: Optional[str] = Field(
        default=None,
        description="Internal author note not exposed to the player"
    )
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
    claims: Optional[List[ClaimConfig]] = Field(
        default=None,
        description="List of claims made by the suspect"
    )
    knowledge: Optional[List[KnowledgeItemConfig]] = Field(
        default=None,
        description="Local knowledge instances the suspect holds"
    )
    profile: Optional[TopicAffinityProfile] = Field(
        default=None,
        description="Behavioral profile modifiers for suspect reactions"
    )
    flavor_slots: Optional[List["FlavorSlotConfig"]] = Field(
        default_factory=list,
        description="Optional cosmetic narrative slots pre-authored for this suspect"
    )

class FlavorOptionConfig(BaseModel):
    id: str = Field(..., description="Unique string identifier for the option")
    text: str = Field(..., description="Canonical textual statement of this flavor option")

class FlavorSlotConfig(BaseModel):
    key: str = Field(..., description="Unique slug for the flavor slot, e.g., 'preferred_food'")
    description: Optional[str] = Field(default=None, description="Internal description of the slot theme")
    trigger_keywords: List[str] = Field(default_factory=list, description="Keywords in player messages that can trigger this slot")
    options: List[FlavorOptionConfig] = Field(default_factory=list, description="Allowed choices for this slot")

class EvidenceConfig(BaseModel):
    id: str = Field(..., description="Stable string identifier for the evidence")
    name: str = Field(..., description="Name of the evidence")
    description: Optional[str] = Field(default=None, description="Public description")
    internal_note: Optional[str] = Field(default=None, description="Internal usage desc not exposed to players")
    related_topic_id: Optional[str] = Field(default=None, description="Topic slug it synergizes with to avoid out-of-context")
    is_mandatory: bool = Field(default=False, description="Whether this evidence is required for correct verdict")

class ChronologyEvent(BaseModel):
    time: str = Field(..., description="Timestamp or description of the event time")
    description: str = Field(..., description="Description of the event")

class ScenarioConfig(BaseModel):
    scenario_code: str = Field(..., description="Stable unique code for the scenario")
    title: str = Field(..., description="Title of the scenario")
    description: Optional[str] = None

    case_summary: Optional[str] = Field(
        default=None,
        description="Resumo interno do caso, conhecido pelo NPC mas não exposto ao jogador"
    )
    
    culprit: str = Field(..., description="Stable id of the guilty suspect")
    suspects: List[SuspectConfig] = Field(..., description="List of suspects")
    evidences: List[EvidenceConfig] = Field(..., description="List of evidences")
    secrets: List[SecretConfig] = Field(..., description="List of secrets")
    chronology: Optional[List[ChronologyEvent]] = None
    topics: Optional[List[TopicConfig]] = Field(default=None, description="Optional list of tracked topics in the scenario")
    motives: Optional[List[MotivationConfig]] = Field(default=None, description="List of possible motives for the crime")
    true_motive_key: Optional[str] = Field(default=None, description="The key of the true motivation (must exist in motives)")
    required_broken_claim_ids: Optional[List[str]] = Field(default_factory=list, description="Claim IDs that must be broken for a correct verdict")
    motive_clues: Optional[List[MotiveClueConfig]] = Field(default_factory=list, description="List of clues pointing to motives")


