from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ResponseMode(str, Enum):
    evasive = "evasive"
    neutral_answer = "neutral_answer"
    clarify = "clarify"
    partial_admission = "partial_admission"
    deny = "deny"
    guarded = "guarded"
    pressured_deflection = "pressured_deflection"
    contradiction_repair = "contradiction_repair"
    context_request = "context_request"
    irritated_repeat = "irritated_repeat"
    final_phrase = "final_phrase"
    # Sprint 3 T5.2
    claim_reaction = "claim_reaction"
    evidence_reaction = "evidence_reaction"
    guarded_answer = "guarded_answer"
    soft_cooperation = "soft_cooperation"

class NpcResponseRenderContext(BaseModel):
    """
    Contrato que o backend envia para a IA.
    A IA não decide mais lógicas do jogo, apenas verbaliza o que este contexto manda.
    """
    response_mode: ResponseMode = ResponseMode.neutral_answer
    npc_stance: str = "neutral"
    allowed_facts: List[str] = Field(
        default_factory=list,
        description="Fatos confirmados/vazados através de evidência"
    )
    allowed_knowledge: List[str] = Field(
        default_factory=list,
        description="Camadas de conhecimento local que o NPC tem permissão de contar neste turno baseado na política de retenção."
    )
    new_knowledge_this_turn: List[str] = Field(
        default_factory=list,
        description="Fatos ou camadas de conhecimento que estão sendo revelados pela *primeira vez* neste turno."
    )
    forbidden_topics: List[str] = Field(default_factory=list)
    must_not_reveal: List[str] = Field(default_factory=list)
    tone_hint: Optional[str] = None
    player_intent: str = "unknown"
    claim_pressure_summary: List[str] = Field(default_factory=list)
    active_topic_id: Optional[str] = None
    # Sprint 3 T5.1
    must_say: List[str] = Field(default_factory=list)
    may_say: List[str] = Field(default_factory=list)
    must_not_say: List[str] = Field(default_factory=list)
    # Memória Narrativa da Sessão (Híbrida e Determinística)
    narrative_memory: "NarrativeMemoryView" = Field(default_factory=lambda: NarrativeMemoryView())


class NarrativeMemoryView(BaseModel):
    relational_notes: List[str] = Field(default_factory=list)
    established_details: List[str] = Field(default_factory=list)
    active_commitments: List[str] = Field(default_factory=list)
