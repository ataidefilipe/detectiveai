from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class MessageIntent(str, Enum):
    ask = "ask"
    pressure = "pressure"
    confront = "confront"
    accuse = "accuse"
    calm = "calm"
    unknown = "unknown"


class MoveType(str, Enum):
    """
    Linguagem de game design para a jogada do turno.
    Derivada de: intent, novelty, specificity, evidence e contexto.
    O backend usa isso para calcular deltas e escolher response_mode.
    """
    explore = "explore"           # Pergunta aberta, tópico novo
    deepen = "deepen"             # Aprofundamento no mesmo tópico
    reframe = "reframe"           # Reformulação (não é repetição)
    pressure = "pressure"         # Pressão direta/acusação
    calm = "calm"                 # Acalmamento / empatia
    confront_evidence = "confront_evidence"  # Apresentação de evidência com contexto
    accuse_soft = "accuse_soft"   # Acusação leve / insinuação
    continue_flow = "continue_flow"  # Fala vaga com tópico herdado


class SensitivityLevel(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"

class NoveltyLevel(str, Enum):
    new = "new"
    repeat = "repeat"
    reframe = "reframe"
    unknown = "unknown"

class SpecificityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class MessageAnalysisResult(BaseModel):
    primary_topic_id: Optional[str] = None
    detected_topic_ids: List[str] = Field(default_factory=list)
    sensitive_topic_ids: List[str] = Field(default_factory=list)
    intent: MessageIntent = MessageIntent.unknown
    sensitivity_hit: SensitivityLevel = SensitivityLevel.none
    novelty: NoveltyLevel = NoveltyLevel.unknown
    specificity: SpecificityLevel = SpecificityLevel.low
    confidence: float = 0.0
    notes: Optional[str] = None
    # T1.3: Campos enriquecidos (backlog12)
    is_reframe: bool = False           # Jogador reformulou a pergunta (não é repetição)
    is_meta_behavior_read: bool = False # Jogador leu o comportamento do NPC ("você hesitou")
    inferred_claim_targets: List[str] = Field(default_factory=list)  # Claims inferidos como alvo
    # Campos semânticos (backlog14 T1.1)
    move_type: Optional[str] = None                          # SemanticMoveType value, None para heurístico
    target_claim_ids: list[str] = Field(default_factory=list) # Claims que o jogador parece mirar
    referenced_evidence_ids: list[int] = Field(default_factory=list) # Evidências mencionadas indiretamente
    analysis_provider: str = "heuristic"                      # "heuristic" | "openai"
    fallback_reason: Optional[str] = None                     # "timeout" | "low_confidence" | "error"

class ConversationEffect(str, Enum):
    none = "none"
    new_topic = "new_topic"
    deeper_topic = "deeper_topic"
    sensitive_touch = "sensitive_touch"
    repeat = "repeat"
    out_of_context = "out_of_context"
    claim_commit = "claim_commit"
    partial_reveal = "partial_reveal"

class NpcShift(str, Enum):
    none = "none"
    more_defensive = "more_defensive"
    more_cooperative = "more_cooperative"
    pressured = "pressured"
    irritated = "irritated"

class StateTransitionResult(BaseModel):
    conversation_effect: ConversationEffect = ConversationEffect.none
    npc_shift: NpcShift = NpcShift.none
    state_deltas: dict = Field(default_factory=dict)
    debug_reason_codes: list[str] = Field(default_factory=list)

class TopicSignal(str, Enum):
    none = "none"
    weak = "weak"
    good = "good"
    strong = "strong"

class SuspectReaction(str, Enum):
    neutro = "neutro"
    evasivo = "evasivo"
    defensivo = "defensivo"
    pressionado = "pressionado"
    cooperativo = "cooperativo"
    irritado = "irritado"

class TopicRead(str, Enum):
    nenhum = "nenhum"
    fraco = "fraco"
    promissor = "promissor"
    sensivel = "sensível"

class NarrativeFeedback(BaseModel):
    suspect_reaction: SuspectReaction = SuspectReaction.neutro
    topic_read: TopicRead = TopicRead.nenhum
    guidance: Optional[str] = None

class PlayerChatInput(BaseModel):
    text: str
    evidence_id: Optional[int] = None


class ChatMessageInfo(BaseModel):
    id: int
    session_id: int
    suspect_id: int
    sender_type: str
    text: str
    evidence_id: Optional[int] = None
    timestamp: str


class TurnDebugTrace(BaseModel):
    message_analysis: Optional[MessageAnalysisResult] = None
    state_transition: Optional[StateTransitionResult] = None
    allowed_knowledge: list[str] = Field(default_factory=list)
    new_knowledge_this_turn: list[str] = Field(default_factory=list)

class ClaimEvent(BaseModel):
    claim_id: str
    broken_by_evidence_id: Optional[int] = None
    broken_by_claim_id: Optional[str] = None
    rewards: List[str] = Field(default_factory=list)


class ConversationMemory(BaseModel):
    """
    Memória curta determinística do interrogatório.
    Janela estruturada dos últimos N turnos — não é memória semântica livre.
    """
    active_topic_id: Optional[str] = None
    last_topic_id: Optional[str] = None
    recent_topic_ids: List[str] = Field(default_factory=list)
    recent_intents: List[str] = Field(default_factory=list)
    recent_evidence_ids: List[int] = Field(default_factory=list)
    recent_claim_ids: List[str] = Field(default_factory=list)
    context_inherited: bool = False


class PlayerTurnResponse(BaseModel):
    player_message: ChatMessageInfo
    npc_message: ChatMessageInfo
    revealed_secrets: list[dict]
    newly_broken_claims: Optional[List[ClaimEvent]] = None
    evidence_effect: str  # "none" | "revealed_secret" | "duplicate" | "out_of_context" | "reaction_only"
    suspect_state: dict
    message_analysis: Optional[MessageAnalysisResult] = None
    state_transition: Optional[StateTransitionResult] = None
    move_type: Optional[str] = None  # T0.1: Expose computed MoveType to frontend
    # Sprint 3 T2.3
    mechanical_effect: Optional[str] = None   # "none"|"revealed_secret"|"broke_claim"|"out_of_context"
    narrative_effect: Optional[str] = None    # "suspect_reacted_defensively"|"no_reaction"|etc

    # Systemic Discrete Feedback removed for MVP-011 (T1)

    # Narrative Feedback (MVP-001)
    narrative_feedback: Optional[NarrativeFeedback] = None

    debug_trace: Optional[TurnDebugTrace] = None

    # T1.1: Contexto conversacional (backlog12)
    active_topic_id: Optional[str] = None
    context_inherited: bool = False
