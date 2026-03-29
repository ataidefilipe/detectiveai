"""
move_classification_service.py

Converte a análise textual da mensagem em uma jogada sistêmica (MoveType).
Essa é a linguagem de game design — traduz intent/novelty/specificity/evidence
em um tipo de jogada que o backend usa para calcular deltas e response_mode.

Regras de prioridade (ordem decrescente):
1. evidence_id presente com contexto → confront_evidence
2. intent == calm → calm
3. intent == pressure/accuse → pressure ou accuse_soft
4. novelty == reframe → reframe
5. tópico novo (sem last_topic) e pergunta aberta → explore
6. mesmo tópico com specificity alta → deepen
7. fala vaga com tópico herdado (context_inherited) → continue_flow
8. fallback → explore
"""

from typing import Optional

from app.api.schemas.chat import (
    ConversationMemory,
    MessageAnalysisResult,
    MessageIntent,
    MoveType,
    NoveltyLevel,
    SpecificityLevel,
)


def classify_move(
    analysis: MessageAnalysisResult,
    context: ConversationMemory,
    evidence_id: Optional[int] = None,
) -> MoveType:
    """
    Classifica a jogada do turno baseado na análise da mensagem e no contexto.

    Args:
        analysis: Resultado da análise heurística da mensagem do jogador.
        context: Memória curta do interrogatório (tópicos recentes, herança, etc).
        evidence_id: ID da evidência apresentada neste turno (None se não houver).

    Returns:
        MoveType representando o tipo de jogada.
    """

    # ── 1. Evidência apresentada ─────────────────────────────────────────────
    # Contextualize = há evidência E há algum tópico ativo (atual ou herdado).
    if evidence_id is not None:
        has_topic_context = (
            bool(analysis.primary_topic_id)
            or bool(context.active_topic_id)
            or bool(context.last_topic_id)
        )
        if has_topic_context:
            return MoveType.confront_evidence
        # Sem contexto algum: ainda é confront_evidence (será marcado out_of_context
        # pela evidence_context_service, mas a jogada em si é de confronto).
        return MoveType.confront_evidence

    # ── 2. Intent explícito de acalmamento ──────────────────────────────────
    if analysis.intent == MessageIntent.calm:
        return MoveType.calm

    # ── 3. Pressão / Acusação ───────────────────────────────────────────────
    if analysis.intent == MessageIntent.pressure:
        return MoveType.pressure

    if analysis.intent == MessageIntent.accuse:
        return MoveType.accuse_soft

    # ── 4. Reformulação (reframe não é repetição) ───────────────────────────
    if analysis.novelty == NoveltyLevel.reframe:
        return MoveType.reframe

    # ── 5. Continuação vaga com tópico herdado ──────────────────────────────
    # Se a mensagem não detectou nenhum tópico mas o contexto tem um,
    # o jogador está continuando o fio da conversa anterior.
    if not analysis.primary_topic_id and context.context_inherited:
        return MoveType.continue_flow

    # ── 6. Aprofundamento no mesmo tópico ────────────────────────────────────
    # Mesmo tópico que estava ativo + especificidade alta → deepen.
    if (
        analysis.primary_topic_id
        and analysis.primary_topic_id == context.active_topic_id
        and analysis.specificity == SpecificityLevel.high
    ):
        return MoveType.deepen

    # ── 7. Exploração ────────────────────────────────────────────────────────
    # Tópico novo OU pergunta aberta sem contexto herdado.
    return MoveType.explore
