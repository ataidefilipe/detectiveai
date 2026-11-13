"""
EPIC 3 (Tarefa 3.1) — Avaliação de Hipóteses do Mural de Investigação.

Avalia conexões e anotações do mural exclusivamente contra os fatos já descobertos
pelo jogador no CaseFile (nunca usa segredos ocultos, culpado ou motivo real).
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from typesafe_sdk import Choice

from app.api.schemas.board import (
    BoardConnectionEvaluationSchema,
    BoardConnectionSchema,
    BoardDataSchema,
    BoardEvaluationResponse,
)
from app.core.exceptions import NotFoundError
from app.core.telemetry import telemetry_logger
from app.infra.db_models import SessionBoardStateModel, SessionModel
from app.services.case_file_service import get_session_case_file
from app.services.typesafe_client import evaluate_system_one, resolve_typesafe_api_key

logger = logging.getLogger(__name__)

_CONNECTION_CRITERIA: Dict[str, str] = {
    "supported_by_facts": (
        "A ligação entre os dois elementos é sustentada diretamente por fatos "
        "confirmados, provas efetivas ou declarações quebradas já presentes no dossiê."
    ),
    "plausible_unproven": (
        "A ligação é uma hipótese investigativa plausível, mas os fatos já "
        "descobertos no dossiê ainda não a comprovam."
    ),
    "contradicted_by_facts": (
        "A ligação ou rótulo contradiz diretamente algum fato já confirmado no dossiê."
    ),
    "vague": (
        "A ligação é genérica ou sem elementos suficientes no dossiê para avaliar."
    ),
}


def _heuristic_evaluate_connections(
    connections: List[BoardConnectionSchema],
    nodes_map: Dict[str, Any],
    case_file: Any,
) -> List[BoardConnectionEvaluationSchema]:
    effective_ev_ids = {ev.evidence_id for ev in case_file.effective_evidences}
    broken_suspect_ids = {
        cl.suspect_id for cl in case_file.claims if cl.status == "broken"
    }
    fact_suspect_ids = {f.suspect_id for f in case_file.confirmed_facts}

    results: List[BoardConnectionEvaluationSchema] = []
    for conn in connections:
        n_from = nodes_map.get(conn.from_id)
        n_to = nodes_map.get(conn.to_id)

        has_effective_ev = False
        has_confirmed_suspect = False
        for node in (n_from, n_to):
            if not node:
                continue
            if node.type == "evidence" and node.ref_id in effective_ev_ids:
                has_effective_ev = True
            if node.type == "suspect" and (
                node.ref_id in broken_suspect_ids or node.ref_id in fact_suspect_ids
            ):
                has_confirmed_suspect = True

        if has_effective_ev and has_confirmed_suspect:
            status = "supported_by_facts"
            conf = 0.65
        elif has_effective_ev or has_confirmed_suspect:
            status = "plausible_unproven"
            conf = 0.50
        else:
            status = "vague"
            conf = 0.40

        results.append(
            BoardConnectionEvaluationSchema(
                connection_id=conn.id,
                from_id=conn.from_id,
                to_id=conn.to_id,
                label=conn.label,
                status=status,
                confidence=conf,
            )
        )
    return results


def _build_summary(evaluations: List[BoardConnectionEvaluationSchema]) -> str:
    if not evaluations:
        return "Nenhuma conexão no mural para analisar. Ligue suspeitos e evidências primeiro."

    counts = {
        "supported_by_facts": 0,
        "plausible_unproven": 0,
        "contradicted_by_facts": 0,
        "vague": 0,
    }
    for ev in evaluations:
        counts[ev.status] = counts.get(ev.status, 0) + 1

    parts = []
    if counts["supported_by_facts"]:
        parts.append(f"{counts['supported_by_facts']} sustentada(s) pelo dossiê")
    if counts["plausible_unproven"]:
        parts.append(f"{counts['plausible_unproven']} hipótese(s) em aberto")
    if counts["contradicted_by_facts"]:
        parts.append(f"{counts['contradicted_by_facts']} em contradição com fatos")
    if counts["vague"]:
        parts.append(f"{counts['vague']} vaga(s)")
    return "Análise do mural: " + ", ".join(parts) + "."


def evaluate_board_hypotheses(
    session_id: int,
    db: Session,
    board_data: Optional[BoardDataSchema] = None,
    provider: Optional[str] = None,
) -> BoardEvaluationResponse:
    """
    Avalia as conexões do mural contra os fatos já descobertos no CaseFile.
    Anti-spoiler: nunca acessa culprit_id, case_summary, true_motive_key ou segredos ocultos.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise NotFoundError(f"Session {session_id} not found.")

    if board_data is None:
        record = (
            db.query(SessionBoardStateModel)
            .filter(SessionBoardStateModel.session_id == session_id)
            .first()
        )
        board_data = (
            BoardDataSchema(**record.board_data)
            if record and record.board_data
            else BoardDataSchema()
        )

    connections = board_data.connections or []
    if not connections:
        return BoardEvaluationResponse(
            session_id=session_id,
            provider="none",
            connections=[],
            summary=_build_summary([]),
        )

    case_file = get_session_case_file(session_id, db)
    nodes_map = {n.id: n for n in (board_data.nodes or [])}

    use_jev = (
        provider == "jev"
        or (provider is None and bool(resolve_typesafe_api_key()))
    )

    if use_jev:
        safe_state = {
            "discovered_facts": [
                {
                    "suspect_id": f.suspect_id,
                    "source_type": f.source_type,
                    "topic_id": f.topic_id,
                    "content": f.content,
                }
                for f in case_file.confirmed_facts
            ],
            "effective_evidences": [
                {"id": e.evidence_id, "name": e.name, "suspect_id": e.suspect_id}
                for e in case_file.effective_evidences
            ],
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "suspect_id": c.suspect_id,
                    "status": c.status,
                    "text": c.text,
                }
                for c in case_file.claims
            ],
            "motive_clues": [
                {"motive_key": m.motive_key, "label": m.label}
                for m in case_file.motive_clues
            ],
            "board_stickers": [
                s.text
                for s in (board_data.stickers or [])
                if s.text and s.id != "sticker-welcome"
            ],
        }

        questions: Dict[str, Any] = {}
        eval_slice = connections[:20]
        for idx, conn in enumerate(eval_slice):
            from_node = nodes_map.get(conn.from_id)
            to_node = nodes_map.get(conn.to_id)
            from_label = (
                f"{from_node.title} ({from_node.type})" if from_node else conn.from_id
            )
            to_label = f"{to_node.title} ({to_node.type})" if to_node else conn.to_id
            conn_note = f" com anotação '{conn.label}'" if conn.label else ""
            questions[f"conn::{idx}"] = Choice(
                instructions=(
                    f"Considerando APENAS os fatos já descobertos no dossiê, qual é o "
                    f"status da conexão entre '{from_label}' e '{to_label}'{conn_note}?"
                ),
                criteria=_CONNECTION_CRITERIA,
            )

        res = evaluate_system_one(state=safe_state, questions=questions)
        if res.ok and res.response is not None:
            choices = getattr(res.response, "choices", {}) or {}
            evaluated: List[BoardConnectionEvaluationSchema] = []
            for idx, conn in enumerate(eval_slice):
                ch = choices.get(f"conn::{idx}")
                status = ch.choice if ch else "vague"
                conf = round(float(ch.confidence), 4) if ch else 0.0
                evaluated.append(
                    BoardConnectionEvaluationSchema(
                        connection_id=conn.id,
                        from_id=conn.from_id,
                        to_id=conn.to_id,
                        label=conn.label,
                        status=status,
                        confidence=conf,
                    )
                )

            telemetry_logger.info(
                json.dumps(
                    {
                        "event": "board_evaluation",
                        "session_id": session_id,
                        "provider": "jev",
                        "connection_count": len(evaluated),
                        "latency_ms": res.latency_ms,
                    }
                )
            )
            return BoardEvaluationResponse(
                session_id=session_id,
                provider="jev",
                connections=evaluated,
                summary=_build_summary(evaluated),
                latency_ms=res.latency_ms,
            )

        # Fallback para heurística caso Jev falhe
        fallback_evals = _heuristic_evaluate_connections(connections, nodes_map, case_file)
        return BoardEvaluationResponse(
            session_id=session_id,
            provider="heuristic",
            connections=fallback_evals,
            summary=_build_summary(fallback_evals),
            latency_ms=res.latency_ms,
            fallback_reason=res.fallback_reason,
        )

    heuristic_evals = _heuristic_evaluate_connections(connections, nodes_map, case_file)
    return BoardEvaluationResponse(
        session_id=session_id,
        provider="heuristic",
        connections=heuristic_evals,
        summary=_build_summary(heuristic_evals),
    )
