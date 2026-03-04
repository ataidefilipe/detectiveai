from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ResponseMode(str, Enum):
    evasive = "evasive"
    neutral_answer = "neutral_answer"
    clarify = "clarify"
    partial_admission = "partial_admission"
    deny = "deny"
    final_phrase = "final_phrase"

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
