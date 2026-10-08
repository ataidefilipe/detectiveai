"""
T1.1 — Schema semântico slim para o classificador GPT.

Versão MVP com 7 campos essenciais (dos 14 do backlog).
Os campos adicionais (sensitive_topic_ids, specificity, novelty,
reasoning_summary, should_inherit_context, player_question_rewrite)
serão adicionados incrementalmente quando houver uso real.
"""
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class SemanticMoveType(str, Enum):
    explore = "explore"
    deepen = "deepen"
    clarify = "clarify"
    pressure = "pressure"
    calm = "calm"
    confront_claim = "confront_claim"
    confront_evidence = "confront_evidence"
    accuse_in_chat = "accuse_in_chat"
    off_topic = "off_topic"
    unknown = "unknown"


class SemanticMessageAnalysisResult(BaseModel):
    """
    Resultado da classificação semântica da mensagem do jogador.

    Campos essenciais apenas — a IA classifica a fala, não joga o jogo.
    Nenhum campo permite decidir culpa, segredo ou veredito.
    """
    primary_topic_id: Optional[str] = None
    detected_topic_ids: List[str] = Field(default_factory=list)
    intent: str = "unknown"
    move_type: SemanticMoveType = SemanticMoveType.unknown
    target_claim_ids: List[str] = Field(default_factory=list)
    referenced_evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
