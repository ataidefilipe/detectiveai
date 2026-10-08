"""
conversation_context_service.py

Responsável por montar a memória curta determinística do interrogatório
a partir do estado persistido e do histórico recente de mensagens.

NÃO é memória semântica — é uma janela estruturada de N turnos.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.api.schemas.chat import ConversationMemory
from app.infra.db_models import (
    NpcChatMessageModel,
    SessionSuspectStateModel,
    SessionSuspectTopicStateModel,
    SessionClaimStateModel,   # NOVO
    SuspectModel,             # NOVO
)
from app.core.config import settings


def build_conversation_context(
    session_id: int,
    suspect_id: int,
    db: Session,
    window_size: Optional[int] = None,
) -> ConversationMemory:
    """
    Constrói o ConversationMemory para o turno atual.

    Estratégia:
    1. Carrega last_topic_id do estado persistido do suspeito.
    2. Lê as últimas `window_size` mensagens (do mais recente para o mais antigo).
    3. Extrai: evidence_ids usados, topic_ids visitados (via topic states tocados).
    4. Decide active_topic_id: primeiro tenta derivar das mensagens recentes,
       depois usa last_topic_id como fallback.
    5. Marca context_inherited=True se o active_topic veio do fallback.

    Args:
        session_id: ID da sessão ativa.
        suspect_id: ID do suspeito sendo interrogado.
        db: Sessão do banco de dados (compartilhada com a transação do turno).
        window_size: Número de mensagens recentes a analisar. Default: settings.CONTEXT_WINDOW_MESSAGES.

    Returns:
        ConversationMemory com o contexto estruturado do interrogatório.
    """
    if window_size is None:
        window_size = settings.CONTEXT_WINDOW_MESSAGES

    # ── 1. Carregar last_topic_id do estado persistido ───────────────────────
    suspect_state = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id,
        SessionSuspectStateModel.suspect_id == suspect_id,
    ).first()

    persisted_last_topic_id: Optional[str] = (
        suspect_state.last_topic_id if suspect_state else None
    )

    # ── 2. Carregar últimas N mensagens (ordem decrescente para recência) ────
    recent_messages = (
        db.query(NpcChatMessageModel)
        .filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id,
        )
        .order_by(NpcChatMessageModel.id.desc())
        .limit(window_size)
        .all()
    )

    # ── 3. Extrair evidence_ids recentes (só das mensagens do jogador) ───────
    recent_evidence_ids: list[int] = []
    for msg in recent_messages:
        if msg.sender_type == "player" and msg.evidence_id is not None:
            if msg.evidence_id not in recent_evidence_ids:
                recent_evidence_ids.append(msg.evidence_id)

    # ── 4. Derivar tópicos recentes via topic states tocados ─────────────────
    # Ordena por tempo de toque decrescente (mais recente primeiro).
    # Filtramos apenas os que foram de fato tocados (times_touched > 0).
    touched_topic_states = (
        db.query(SessionSuspectTopicStateModel)
        .filter(
            SessionSuspectTopicStateModel.session_id == session_id,
            SessionSuspectTopicStateModel.suspect_id == suspect_id,
            SessionSuspectTopicStateModel.times_touched > 0,
        )
        .all()
    )

    # Construímos a lista de tópicos recentes priorizando:
    # - o last_topic_id (mais recente) primeiro
    # - depois os demais tocados, sem repetir
    recent_topic_ids: list[str] = []
    if persisted_last_topic_id:
        recent_topic_ids.append(persisted_last_topic_id)

    for ts in touched_topic_states:
        if ts.topic_id not in recent_topic_ids:
            recent_topic_ids.append(ts.topic_id)

    # Limita a janela a window_size tópicos
    recent_topic_ids = recent_topic_ids[:window_size]

    # ── 5. Resolver active_topic_id ──────────────────────────────────────────
    # O active_topic_id é o tópico mais saliente para este turno.
    # Se há um last_topic_id persistido, ele é o candidato principal.
    # context_inherited = True significa que não há tópico novo explícito
    # neste turno — estamos herdando o contexto anterior.
    active_topic_id = persisted_last_topic_id
    context_inherited = active_topic_id is not None

    # ── 6. Carregar claims recentes (Sprint 2 T3.1) ─────────────────────────
    recent_claim_ids: list[str] = []

    claim_states = db.query(SessionClaimStateModel).filter(
        SessionClaimStateModel.session_id == session_id,
        SessionClaimStateModel.suspect_id == suspect_id,
    ).all()

    for cs in claim_states:
        # Claims quebradas recentemente
        if cs.status == "broken" and cs.claim_id not in recent_claim_ids:
            recent_claim_ids.append(cs.claim_id)

        # Claims reveladas (ativas e conhecidas pelo jogador)
        if cs.is_revealed and cs.status == "active" and cs.claim_id not in recent_claim_ids:
            recent_claim_ids.append(cs.claim_id)

    # Cruzar claims com tópico ativo
    if persisted_last_topic_id:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
        if suspect and suspect.claims:
            for c in suspect.claims:
                if c.get("topic_id") == persisted_last_topic_id:
                    cid = c.get("claim_id")
                    if cid not in recent_claim_ids:
                        recent_claim_ids.append(cid)

    return ConversationMemory(
        active_topic_id=active_topic_id,
        last_topic_id=persisted_last_topic_id,
        recent_topic_ids=recent_topic_ids,
        recent_intents=[],  # Preenchido por turns futuros quando armazenarmos intent por msg
        recent_evidence_ids=recent_evidence_ids,
        recent_claim_ids=recent_claim_ids,  # ← agora preenchido
        context_inherited=context_inherited,
    )
