"""
Benchmark e calibração PT-BR (Tarefa 0.2 — Backlog 15).

Compara Heuristic vs OpenAI vs Jev (TypeSafe AI) nos casos curados da Sessão 9
e goldens de classificação e guard pós-resposta.

Uso:
    python scripts/benchmark_jev_interrogation.py
    python scripts/benchmark_jev_interrogation.py --providers heuristic,jev
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score

load_dotenv()

from app.core.config import settings
from app.services.message_classifier import HeuristicMessageClassifier
from app.services.npc_response_guard import guard_npc_response
from app.services.typesafe_client import evaluate_system_one, resolve_typesafe_api_key

FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "jev_calibration_cases.json"


def _percentile(values: List[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return float(ordered[idx])


def _load_fixture(path: Path = FIXTURE_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _classify_with_jev(case: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.message_classifier_jev import JevSemanticMessageClassifier

    classifier = JevSemanticMessageClassifier()
    t0 = time.perf_counter()
    res = classifier.classify(
        case["text"],
        available_topics=ctx["topics"],
        player_history=case.get("player_history", []),
        claims=ctx["claims"],
        evidences=ctx["evidences"],
        active_topic_id=case.get("active_topic_id"),
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if res.analysis_provider != "jev":
        return {"error": res.fallback_reason or "fallback", "latency_ms": elapsed_ms}

    return {
        "primary_topic_id": res.primary_topic_id,
        "intent": res.intent.value,
        "specificity": res.specificity.value,
        "is_reframe": res.is_reframe,
        "is_repeat": res.novelty.value == "repeat",
        "is_meta_behavior_read": res.is_meta_behavior_read,
        "target_claim_ids": res.target_claim_ids,
        "referenced_evidence_ids": res.referenced_evidence_ids,
        "latency_ms": elapsed_ms,
    }


def _guard_with_jev(case: Dict[str, Any]) -> Dict[str, Any]:
    questions = {
        "leak_hidden_secret": Noul(
            instructions="A fala do suspeito revela, confirma ou insinua diretamente algum dos hidden_secrets?"
        ),
        "leak_true_motive": Noul(
            instructions="A fala do suspeito revela ou insinua o motivo real (true_motive) do crime?"
        ),
        "unauthorized_confession": Noul(
            instructions="O suspeito está confessando a autoria do crime/homicídio sem autorização em must_say?"
        ),
        "contradicts_active_claims": Noul(
            instructions="O suspeito contradiz frontalmente alguma declaração em active_claims?"
        ),
    }
    state = {
        "npc_response": case["response_text"],
        "hidden_secrets": case.get("hidden_secrets", []),
        "true_motive": case.get("true_motive"),
        "active_claims": case.get("active_claims", []),
        "must_say": case.get("must_say", []),
        "response_mode": case.get("response_mode"),
    }
    res = evaluate_system_one(state=state, questions=questions)
    if not res.ok or res.response is None:
        return {"error": res.fallback_reason or res.error, "latency_ms": res.latency_ms}

    nouls = res.response.nouls
    blocked = any(
        nouls[k].noul >= 0.75
        for k in ("leak_hidden_secret", "leak_true_motive", "unauthorized_confession", "contradicts_active_claims")
    )
    return {
        "blocked": blocked,
        "probs": {k: round(nouls[k].noul, 3) for k in nouls},
        "latency_ms": res.latency_ms,
    }


def run_classification_benchmark(providers: List[str], fixture: Dict[str, Any]) -> Dict[str, Any]:
    ctx = fixture["scenario_context"]
    cases = fixture["classification_cases"]
    summary: Dict[str, Any] = {}

    for provider in providers:
        latencies: List[int] = []
        topic_hits = 0
        intent_hits = 0
        trait_hits = 0
        trait_total = 0
        errors = 0

        heuristic = HeuristicMessageClassifier() if provider == "heuristic" else None
        openai_cls = None
        if provider == "openai":
            from app.services.message_classifier_openai import OpenAISemanticMessageClassifier
            openai_cls = OpenAISemanticMessageClassifier()

        for case in cases:
            expected = case["expected"]
            t0 = time.perf_counter()

            if provider == "heuristic":
                res = heuristic.classify(
                    case["text"],
                    available_topics=ctx["topics"],
                    player_history=case.get("player_history", []),
                    active_topic_id=case.get("active_topic_id"),
                )
                pred = {
                    "primary_topic_id": res.primary_topic_id,
                    "intent": res.intent.value,
                    "specificity": res.specificity.value,
                    "is_reframe": res.is_reframe,
                    "is_repeat": res.novelty.value == "repeat",
                    "is_meta_behavior_read": res.is_meta_behavior_read,
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                }
            elif provider == "openai":
                res = openai_cls.classify(
                    case["text"],
                    available_topics=ctx["topics"],
                    player_history=case.get("player_history", []),
                    claims=ctx["claims"],
                    evidences=ctx["evidences"],
                    active_topic_id=case.get("active_topic_id"),
                )
                pred = {
                    "primary_topic_id": res.primary_topic_id,
                    "intent": res.intent.value,
                    "specificity": res.specificity.value,
                    "is_reframe": res.is_reframe,
                    "is_repeat": res.novelty.value == "repeat",
                    "is_meta_behavior_read": res.is_meta_behavior_read,
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                }
            elif provider == "jev":
                pred = _classify_with_jev(case, ctx)
                if "error" in pred:
                    errors += 1
                    continue
            else:
                continue

            latencies.append(pred["latency_ms"])
            if pred["primary_topic_id"] == expected["primary_topic_id"]:
                topic_hits += 1
            if pred["intent"] == expected["intent"]:
                intent_hits += 1

            for trait in ("specificity", "is_reframe", "is_repeat", "is_meta_behavior_read"):
                trait_total += 1
                if pred[trait] == expected[trait]:
                    trait_hits += 1

        total = max(1, len(cases) - errors)
        summary[provider] = {
            "cases": len(cases),
            "errors": errors,
            "topic_acc": round(topic_hits / total, 3),
            "intent_acc": round(intent_hits / total, 3),
            "traits_acc": round(trait_hits / max(1, trait_total), 3),
            "latency_mean_ms": round(sum(latencies) / max(1, len(latencies)), 1),
            "latency_p95_ms": _percentile(latencies, 95),
        }

    return summary


def run_guard_benchmark(providers: List[str], fixture: Dict[str, Any]) -> Dict[str, Any]:
    cases = fixture["guard_cases"]
    summary: Dict[str, Any] = {}

    for provider in providers:
        hits = 0
        fp = 0
        fn = 0
        errors = 0
        latencies: List[int] = []

        for case in cases:
            expected_blocked = case["expected_blocked"]
            t0 = time.perf_counter()

            if provider == "literal":
                _, blocked = guard_npc_response(
                    response_text=case["response_text"],
                    hidden_secrets=case.get("hidden_secrets", []),
                    true_motive=case.get("true_motive"),
                )
                lat = int((time.perf_counter() - t0) * 1000)
            elif provider == "jev":
                pred = _guard_with_jev(case)
                if "error" in pred:
                    errors += 1
                    continue
                blocked = pred["blocked"]
                lat = pred["latency_ms"]
            else:
                continue

            latencies.append(lat)
            if blocked == expected_blocked:
                hits += 1
            elif blocked and not expected_blocked:
                fp += 1
            else:
                fn += 1

        total = max(1, len(cases) - errors)
        summary[provider] = {
            "cases": len(cases),
            "errors": errors,
            "accuracy": round(hits / total, 3),
            "false_positives": fp,
            "false_negatives": fn,
            "latency_mean_ms": round(sum(latencies) / max(1, len(latencies)), 1),
            "latency_p95_ms": _percentile(latencies, 95),
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark PT-BR Heuristic vs OpenAI vs Jev")
    parser.add_argument(
        "--providers",
        default="",
        help="Lista separada por vírgula (ex: heuristic,openai,jev). Padrão: detecta chaves disponíveis.",
    )
    args = parser.parse_args()

    fixture = _load_fixture()
    if args.providers.strip():
        cls_providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    else:
        cls_providers = ["heuristic"]
        if os.getenv("OPENAI_API_KEY"):
            cls_providers.append("openai")
        if resolve_typesafe_api_key():
            cls_providers.append("jev")

    guard_providers = ["literal"]
    if "jev" in cls_providers:
        guard_providers.append("jev")

    print("=== Classificação de Mensagens ===")
    cls_summary = run_classification_benchmark(cls_providers, fixture)
    print(json.dumps(cls_summary, indent=2, ensure_ascii=False))

    print("\n=== Guard Pós-Resposta ===")
    guard_summary = run_guard_benchmark(guard_providers, fixture)
    print(json.dumps(guard_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
