"""
Guardião pós-resposta do NPC (EPIC 1 — Backlog 15).

Combina fast-path literal com verificação semântica paralela via Jev (noul + score)
para bloquear vazamentos por paráfrase, confissões não autorizadas e contradições
de claims ainda ativas, com fallback diegético por ResponseMode.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from typesafe_sdk import Noul, Score

from app.core.config import settings
from app.core.telemetry import telemetry_logger
from app.services.typesafe_client import evaluate_system_one

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK_TEXT = "Não tenho nada a dizer sobre isso."

_MODE_FALLBACK_MAP: Dict[str, str] = {
    "evasive": "Prefiro não entrar nesses detalhes agora, detetive.",
    "deny": "Isso não faz sentido. Eu não tenho nada a ver com o que você está insinuando.",
    "guarded": "Vou manter o que já disse. Não tenho mais nada a declarar sobre esse ponto.",
    "guarded_answer": "Vou manter o que já disse. Não tenho mais nada a declarar sobre esse ponto.",
    "pressured_deflection": "Você está tentando me colocar contra a parede sem motivo… não vou responder a isso.",
    "contradiction_repair": "Reconheço que esse ponto é delicado, mas não vou ir além do que já está claro.",
    "partial_admission": "Admito apenas o que já está diante de nós, nada além disso.",
    "claim_reaction": "Preciso pensar melhor antes de responder sobre isso.",
    "evidence_reaction": "Eu vejo o que você está mostrando, mas isso não prova o que você pensa.",
    "irritated_repeat": "Já respondi a isso antes, detetive. Não vou repetir.",
    "context_request": "Seja mais específico sobre o que você quer saber.",
}


@dataclass(frozen=True)
class GuardEvaluationResult:
    """Resultado completo da avaliação do guard pós-resposta."""

    text: str
    was_blocked: bool
    provider: str = "literal"
    reason: Optional[str] = None
    probabilities: Dict[str, float] = field(default_factory=dict)
    latency_ms: int = 0
    fallback_reason: Optional[str] = None


def _check_literal_guard(
    response_text: str,
    hidden_secrets: List[str],
    true_motive: Optional[str] = None,
) -> Optional[str]:
    """Fast-path determinístico por substring literal. Retorna a razão do bloqueio ou None."""
    text_lower = response_text.lower()
    for secret in hidden_secrets:
        if secret and secret.lower() in text_lower:
            return "literal_secret_match"

    if true_motive and true_motive.lower() in text_lower:
        return "literal_motive_match"

    return None


def _build_contextual_fallback(
    response_mode: Optional[str] = None,
    must_say: Optional[List[str]] = None,
) -> str:
    """
    Constrói resposta de contenção diegética compatível com o ResponseMode.
    Quando há fatos obrigatórios autorizados pelo backend (must_say), preserva-os
    de forma segura sem vazar a confissão/spoiler que motivou o bloqueio.
    """
    base = _MODE_FALLBACK_MAP.get(response_mode or "", _DEFAULT_FALLBACK_TEXT)
    clean_must_say = [m.strip() for m in (must_say or []) if isinstance(m, str) and m.strip()]
    if clean_must_say:
        facts_text = " ".join(clean_must_say)
        return f"{base} O que posso confirmar é apenas isto: {facts_text}"
    return base


def build_guard_retry_instruction(
    reason: Optional[str],
    must_say: Optional[List[str]] = None,
) -> str:
    """Gera instrução corretiva curta para a única tentativa de regeneração na LLM."""
    reason_hints = {
        "literal_secret_match": "Sua resposta anterior revelou literalmente um segredo oculto. Não mencione esse fato.",
        "literal_motive_match": "Sua resposta anterior revelou o motivo real do crime. Não mencione ou insinue esse motivo.",
        "leak_hidden_secret": "Sua resposta anterior insinuou ou revelou um segredo que você ainda esconde. Não revele nem dê pistas sobre isso.",
        "leak_true_motive": "Sua resposta anterior insinuou o motivo real do crime. Mantenha esse motivo em segredo.",
        "unauthorized_confession": "Você NÃO pode confessar autoria do crime ou agressão. Negue ou se limite apenas aos fatos autorizados.",
        "contradicts_active_claims": "Sua resposta anterior contradisse sua versão oficial ativa. Mantenha consistência com suas declarações.",
        "mode_violation": "Sua resposta anterior fugiu do seu tom/modo de atuação atual. Ajuste a postura emocional conforme SEU TOM AGORA.",
        "repeats_last_npc_reply": "Sua resposta anterior repetiu quase a mesma fala e justificativa do turno passado. Reaja diretamente ao novo ângulo do detetive sem repetir a resposta anterior.",
        "unnatural_or_meta_refusal": "Sua resposta anterior soou mecânica/robótica ou recusou secamente sem reação humana. Responda como uma pessoa real em interrogatório, sem frases de sistema.",
    }
    base_hint = reason_hints.get(
        reason or "",
        "Sua resposta anterior violou restrições do turno. Reescreva respeitando apenas os fatos autorizados.",
    )
    clean_must = [m.strip() for m in (must_say or []) if isinstance(m, str) and m.strip()]
    if clean_must:
        facts = "; ".join(clean_must)
        return f"{base_hint} Preserve obrigatoriamente estes fatos autorizados: {facts}."
    return base_hint


def evaluate_npc_response_guard(
    response_text: str,
    hidden_secrets: List[str],
    true_motive: Optional[str] = None,
    culprit_name: Optional[str] = None,
    internal_notes: Optional[List[str]] = None,
    active_claims: Optional[List[str]] = None,
    must_say: Optional[List[str]] = None,
    response_mode: Optional[str] = None,
    provider: Optional[str] = None,
    player_text: Optional[str] = None,
    last_npc_reply: Optional[str] = None,
) -> GuardEvaluationResult:
    """
    Avalia a fala gerada pelo NPC antes de entregá-la ao jogador.
    1. Executa fast-path literal (custo zero).
    2. Se provider == "jev", executa checagem semântica paralela (noul + score).
    """
    # 1. Barreira literal rápida
    literal_reason = _check_literal_guard(response_text, hidden_secrets, true_motive)
    if literal_reason:
        logger.warning(f"[guard] npc_response_guard_triggered ({literal_reason})")
        return GuardEvaluationResult(
            text=_build_contextual_fallback(response_mode, must_say),
            was_blocked=True,
            provider="literal",
            reason=literal_reason,
        )

    active_provider = (provider or settings.NPC_RESPONSE_GUARD_PROVIDER or "literal").lower()
    if active_provider != "jev":
        return GuardEvaluationResult(
            text=response_text,
            was_blocked=False,
            provider="literal",
        )

    # 2. Barreira semântica com Jev (noul + score em paralelo)
    questions: Dict[str, Any] = {
        "unauthorized_confession": Noul(
            instructions=(
                "O suspeito está confessando a autoria do crime/homicídio principal "
                "sem que isso esteja autorizado em must_say?"
            )
        ),
        "mode_adherence": Score(
            instructions="Quão fiel a fala do suspeito está à diretriz de atuação (response_mode)?",
            criteria=[
                "violou totalmente a diretriz",
                "desviou bastante",
                "adequado com pequenas falhas",
                "totalmente fiel ao modo",
            ],
        ),
    }

    if hidden_secrets or internal_notes:
        questions["leak_hidden_secret"] = Noul(
            instructions=(
                "A fala do suspeito revela, confirma ou insinua diretamente "
                "algum dos hidden_secrets ou internal_notes?"
            )
        )

    if true_motive:
        questions["leak_true_motive"] = Noul(
            instructions="A fala do suspeito revela ou insinua o motivo real (true_motive) do crime?"
        )

    if active_claims:
        questions["contradicts_active_claims"] = Noul(
            instructions=(
                "O suspeito contradiz frontalmente alguma de suas declarações ainda "
                "ativas (active_claims) que não foram quebradas?"
            )
        )

    if last_npc_reply and last_npc_reply.strip():
        questions["repeats_last_npc_reply"] = Noul(
            instructions=(
                "A nova fala do suspeito praticamente repete o conteúdo, desculpa ou "
                "justificativa de sua fala imediatamente anterior (last_npc_reply), sem "
                "reagir ao novo ângulo da pergunta do jogador?"
            )
        )

    if player_text and player_text.strip():
        questions["unnatural_or_meta_refusal"] = Noul(
            instructions=(
                "A fala do suspeito soa robótica/metalinguística (ex.: diz que não tem "
                "informações ou não pode inventar) ou recusa secamente sem reação humana "
                "compatível com um interrogatório?"
            )
        )

    state = {
        "npc_response": response_text,
        "player_text": player_text,
        "last_npc_reply": last_npc_reply,
        "culprit_name": culprit_name,
        "hidden_secrets": hidden_secrets or [],
        "internal_notes": internal_notes or [],
        "true_motive": true_motive,
        "active_claims": active_claims or [],
        "must_say": must_say or [],
        "response_mode": response_mode,
    }

    eval_res = evaluate_system_one(state=state, questions=questions)
    if not eval_res.ok or eval_res.response is None:
        return GuardEvaluationResult(
            text=response_text,
            was_blocked=False,
            provider="literal_fallback",
            latency_ms=eval_res.latency_ms,
            fallback_reason=eval_res.fallback_reason,
        )

    nouls = getattr(eval_res.response, "nouls", {}) or {}
    scores = getattr(eval_res.response, "scores", {}) or {}

    probs: Dict[str, float] = {
        k: round(float(v.noul), 4) for k, v in nouls.items() if hasattr(v, "noul")
    }
    if "mode_adherence" in scores and hasattr(scores["mode_adherence"], "score"):
        probs["mode_adherence"] = round(float(scores["mode_adherence"].score), 4)

    block_reason: Optional[str] = None
    if probs.get("leak_hidden_secret", 0.0) >= settings.JEV_GUARD_LEAK_THRESHOLD:
        block_reason = "leak_hidden_secret"
    elif probs.get("leak_true_motive", 0.0) >= settings.JEV_GUARD_LEAK_THRESHOLD:
        block_reason = "leak_true_motive"
    elif probs.get("unauthorized_confession", 0.0) >= settings.JEV_GUARD_CONFESSION_THRESHOLD:
        block_reason = "unauthorized_confession"
    elif probs.get("contradicts_active_claims", 0.0) >= settings.JEV_GUARD_CONTRADICTION_THRESHOLD:
        block_reason = "contradicts_active_claims"
    elif (
        response_mode in {"evasive", "deny", "guarded", "guarded_answer", "pressured_deflection"}
        and probs.get("mode_adherence", 3.0) < settings.JEV_GUARD_MODE_MIN_SCORE
    ):
        block_reason = "mode_violation"
    elif probs.get("repeats_last_npc_reply", 0.0) >= settings.JEV_GUARD_QUALITY_THRESHOLD:
        block_reason = "repeats_last_npc_reply"
    elif probs.get("unnatural_or_meta_refusal", 0.0) >= settings.JEV_GUARD_QUALITY_THRESHOLD:
        block_reason = "unnatural_or_meta_refusal"

    if block_reason:
        logger.warning(f"[guard] npc_response_guard_triggered (jev:{block_reason})")
        telemetry_logger.info(
            json.dumps(
                {
                    "event": "npc_guard_blocked",
                    "provider": "jev",
                    "reason": block_reason,
                    "response_mode": response_mode,
                    "probabilities": probs,
                    "latency_ms": eval_res.latency_ms,
                }
            )
        )
        return GuardEvaluationResult(
            text=_build_contextual_fallback(response_mode, must_say),
            was_blocked=True,
            provider="jev",
            reason=block_reason,
            probabilities=probs,
            latency_ms=eval_res.latency_ms,
        )

    return GuardEvaluationResult(
        text=response_text,
        was_blocked=False,
        provider="jev",
        probabilities=probs,
        latency_ms=eval_res.latency_ms,
    )


def guard_npc_response(
    response_text: str,
    hidden_secrets: List[str],
    true_motive: Optional[str] = None,
    culprit_name: Optional[str] = None,
    internal_notes: Optional[List[str]] = None,
    active_claims: Optional[List[str]] = None,
    must_say: Optional[List[str]] = None,
    response_mode: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Wrapper retrocompatível para o guard pós-resposta.
    Returns: (texto_final, was_blocked)
    """
    res = evaluate_npc_response_guard(
        response_text=response_text,
        hidden_secrets=hidden_secrets,
        true_motive=true_motive,
        culprit_name=culprit_name,
        internal_notes=internal_notes,
        active_claims=active_claims,
        must_say=must_say,
        response_mode=response_mode,
        provider=provider,
    )
    return res.text, res.was_blocked
