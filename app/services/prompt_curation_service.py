"""
Curadoria dinâmica de contexto pré-prompt via Jev (EPIC 6 — Tarefa 6.1).

Seleciona estritamente os itens de may_say, active_claims e trocas antigas
fora da janela recente que são pertinentes à fala atual do jogador, evitando
despejo de fatos não solicitados e esquecimento em interrogatórios longos.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from typesafe_sdk import Noul

from app.core.config import settings
from app.core.telemetry import telemetry_logger
from app.services.typesafe_client import evaluate_system_one, resolve_typesafe_api_key

logger = logging.getLogger(__name__)

_MIN_ACCUMULATED_ITEMS = 4
_RECENT_TAIL_SIZE = 10
_MAX_OLDER_HISTORY_CANDIDATES = 12
_MAX_SEMANTIC_PINNED_HISTORY = 3


@dataclass(frozen=True)
class PromptCurationResult:
    """Resultado da curadoria pré-prompt."""

    may_say: List[str]
    active_claims: List[str]
    pinned_message_ids: List[int] = field(default_factory=list)
    curated: bool = False
    provider: str = "none"
    latency_ms: int = 0
    fallback_reason: Optional[str] = None
    original_may_say_count: int = 0
    curated_may_say_count: int = 0
    original_active_claims_count: int = 0
    curated_active_claims_count: int = 0
    semantic_pinned_history_count: int = 0


def curate_prompt_context(
    *,
    player_text: str,
    may_say: Optional[List[str]] = None,
    active_claims: Optional[List[str]] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    effective_message_ids: Optional[List[int]] = None,
    must_say: Optional[List[str]] = None,
    active_topic_id: Optional[str] = None,
    response_mode: Optional[str] = None,
    enabled: Optional[bool] = None,
    provider: Optional[str] = None,
    threshold: Optional[float] = None,
) -> PromptCurationResult:
    """
    Filtra may_say, active_claims e seleciona até 3 trocas antigas relevantes
    em uma única chamada paralela ao Jev quando há acúmulo de contexto.

    Invariantes:
    - Nunca altera must_say ou a mensagem atual do jogador.
    - Sem chave Jev, com feature desabilitada, em final_phrase ou sem acúmulo,
      retorna os dados originais sem chamada de rede.
    - Em caso de falha/timeout do Jev, degrada mantendo todos os dados originais.
    """
    raw_may_say = [m for m in (may_say or []) if isinstance(m, str) and m.strip()]
    raw_claims = [c for c in (active_claims or []) if isinstance(c, str) and c.strip()]
    history = list(chat_history or [])
    effective_set = set(effective_message_ids or [])

    base_result = PromptCurationResult(
        may_say=raw_may_say,
        active_claims=raw_claims,
        pinned_message_ids=[],
        curated=False,
        provider="none",
        original_may_say_count=len(raw_may_say),
        curated_may_say_count=len(raw_may_say),
        original_active_claims_count=len(raw_claims),
        curated_active_claims_count=len(raw_claims),
        semantic_pinned_history_count=0,
    )

    is_enabled = settings.JEV_PROMPT_CURATION_ENABLED if enabled is None else enabled
    if not is_enabled or response_mode == "final_phrase" or not (player_text or "").strip():
        return base_result

    use_jev = provider == "jev" or (
        provider is None and bool(resolve_typesafe_api_key())
    )
    if not use_jev:
        return base_result

    # Candidatos de histórico fora da janela recente (10 últimas mensagens) e ainda não pinados
    older_slice = history[:-_RECENT_TAIL_SIZE] if len(history) > _RECENT_TAIL_SIZE else []
    older_candidates = [
        m for m in older_slice
        if m.get("id") is not None and m.get("id") not in effective_set and (m.get("text") or "").strip()
    ][-_MAX_OLDER_HISTORY_CANDIDATES:]

    has_accumulation = (len(raw_may_say) + len(raw_claims) >= _MIN_ACCUMULATED_ITEMS) or bool(older_candidates)
    if not has_accumulation:
        return base_result

    questions: Dict[str, Any] = {}
    for idx, text in enumerate(raw_may_say):
        questions[f"may_say::{idx}"] = Noul(
            instructions=(
                f"O fato opcional may_say[{idx}] ('{text[:140]}') é diretamente pertinente "
                "para responder à pergunta atual do detetive sem despejar assunto fora de hora?"
            )
        )

    for idx, text in enumerate(raw_claims):
        questions[f"claim::{idx}"] = Noul(
            instructions=(
                f"A declaração oficial active_claims[{idx}] ('{text[:140]}') precisa estar no "
                "contexto porque a pergunta atual do detetive toca nesse tema, horário ou álibi?"
            )
        )

    for m in older_candidates:
        mid = m["id"]
        sender = m.get("sender", "player")
        mtext = (m.get("text") or "")[:140]
        questions[f"hist::{mid}"] = Noul(
            instructions=(
                f"A troca antiga id={mid} ({sender}: '{mtext}') é importante para manter "
                "continuidade, cobrar coerência ou lembrar promessa relevante para a fala atual?"
            )
        )

    if not questions:
        return base_result

    state = {
        "player_text": player_text,
        "active_topic_id": active_topic_id,
        "must_say": must_say or [],
        "may_say_candidates": [{"idx": i, "text": t} for i, t in enumerate(raw_may_say)],
        "active_claim_candidates": [{"idx": i, "text": t} for i, t in enumerate(raw_claims)],
        "older_history_candidates": [
            {"id": m["id"], "sender": m.get("sender"), "text": m.get("text")}
            for m in older_candidates
        ],
    }

    eval_res = evaluate_system_one(state=state, questions=questions)
    if not eval_res.ok or eval_res.response is None:
        return PromptCurationResult(
            may_say=raw_may_say,
            active_claims=raw_claims,
            pinned_message_ids=[],
            curated=False,
            provider="fallback",
            latency_ms=eval_res.latency_ms,
            fallback_reason=eval_res.fallback_reason or "error",
            original_may_say_count=len(raw_may_say),
            curated_may_say_count=len(raw_may_say),
            original_active_claims_count=len(raw_claims),
            curated_active_claims_count=len(raw_claims),
            semantic_pinned_history_count=0,
        )

    rel_threshold = (
        settings.JEV_CURATION_RELEVANCE_THRESHOLD if threshold is None else threshold
    )
    nouls = getattr(eval_res.response, "nouls", {}) or {}

    curated_may_say: List[str] = []
    for idx, text in enumerate(raw_may_say):
        n = nouls.get(f"may_say::{idx}")
        prob = float(n.noul) if n is not None and hasattr(n, "noul") else 1.0
        if prob >= rel_threshold:
            curated_may_say.append(text)

    curated_claims: List[str] = []
    for idx, text in enumerate(raw_claims):
        n = nouls.get(f"claim::{idx}")
        prob = float(n.noul) if n is not None and hasattr(n, "noul") else 1.0
        if prob >= rel_threshold:
            curated_claims.append(text)

    scored_history: List[tuple[float, int]] = []
    for m in older_candidates:
        mid = m["id"]
        n = nouls.get(f"hist::{mid}")
        prob = float(n.noul) if n is not None and hasattr(n, "noul") else 0.0
        if prob >= rel_threshold:
            scored_history.append((prob, mid))

    # Seleciona os mais relevantes (até _MAX_SEMANTIC_PINNED_HISTORY), preservando ordem cronológica
    scored_history.sort(key=lambda item: item[0], reverse=True)
    top_ids = {mid for _, mid in scored_history[:_MAX_SEMANTIC_PINNED_HISTORY]}
    pinned_ids = [m["id"] for m in older_candidates if m["id"] in top_ids]

    telemetry_logger.info(
        json.dumps(
            {
                "event": "prompt_curation",
                "provider": "jev",
                "may_say_kept": len(curated_may_say),
                "may_say_total": len(raw_may_say),
                "claims_kept": len(curated_claims),
                "claims_total": len(raw_claims),
                "pinned_history": len(pinned_ids),
                "latency_ms": eval_res.latency_ms,
            }
        )
    )

    return PromptCurationResult(
        may_say=curated_may_say,
        active_claims=curated_claims,
        pinned_message_ids=pinned_ids,
        curated=True,
        provider="jev",
        latency_ms=eval_res.latency_ms,
        original_may_say_count=len(raw_may_say),
        curated_may_say_count=len(curated_may_say),
        original_active_claims_count=len(raw_claims),
        curated_active_claims_count=len(raw_claims) if not raw_claims else len(curated_claims),
        semantic_pinned_history_count=len(pinned_ids),
    )
