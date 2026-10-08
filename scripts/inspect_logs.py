"""
scripts/inspect_logs.py

Utilitário para visualizar e exportar os logs analíticos de turnos (turn_logs)
e vereditos (verdict_logs) do banco SQLite (game.db).

Uso:
    python scripts/inspect_logs.py --sessions
    python scripts/inspect_logs.py --session 1
    python scripts/inspect_logs.py --export-csv turn_logs.csv
"""

import argparse
import json
import csv
import os
import sys

# Adicionar root do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.db import SessionLocal
from app.infra.db_models import TurnLogModel, VerdictLogModel, SessionModel


def list_sessions(db):
    sessions = db.query(SessionModel).order_by(SessionModel.id.desc()).all()
    if not sessions:
        print("Nenhuma sessão encontrada.")
        return

    print("\n=== SESSÕES REGISTRADAS ===")
    print(f"{'ID':<6} | {'Cenário':<8} | {'Status':<12} | {'Resultado':<10} | {'Turnos':<8} | {'Criada em'}")
    print("-" * 75)
    for s in sessions:
        turn_count = db.query(TurnLogModel).filter(TurnLogModel.session_id == s.id).count()
        print(f"{s.id:<6} | {s.scenario_id:<8} | {s.status:<12} | {str(s.result_type):<10} | {turn_count:<8} | {s.created_at}")
    print()


def show_session_details(db, session_id: int):
    verdict = db.query(VerdictLogModel).filter(VerdictLogModel.session_id == session_id).first()
    turns = db.query(TurnLogModel).filter(TurnLogModel.session_id == session_id).order_by(TurnLogModel.turn_number.asc()).all()

    print(f"\n================ RELATÓRIO DA SESSÃO {session_id} ================")
    if verdict:
        print(f"Resultado: {verdict.result_type.upper()} | Culpado Acusado: {verdict.chosen_suspect_id} | Real: {verdict.real_culprit_id}")
        print(f"Motivo: {verdict.chosen_motive_key} ({verdict.motive_result}) | Evidências: {verdict.evidence_ids}")
        if verdict.session_summary:
            print(f"Duração: {verdict.session_summary.get('duration_seconds')}s | Total de Turnos: {verdict.session_summary.get('total_turns')}")
    else:
        print("Sessão em andamento (sem veredito).")

    print(f"\nTotal de Turnos: {len(turns)}")
    for t in turns:
        ai_data = t.ai or {}
        effects = t.effects or {}
        print("-" * 75)
        print(f"Turno #{t.turn_number} [Suspeito {t.suspect_id}] - {t.created_at}")
        print(f"  Jogador: \"{t.player_text}\"")
        if t.evidence_id:
            print(f"  Evidência: #{t.evidence_id} (Efeito: {t.evidence_effect})")
        print(f"  Intenção: {t.intent} | Move: {t.move_type} | Tópico: {t.primary_topic_id}")
        
        sb = t.state_before or {}
        sa = t.state_after or {}
        dp = round(sa.get("pressure", 0) - sb.get("pressure", 0), 1)
        dpat = round(sa.get("patience", 0) - sb.get("patience", 0), 1)
        print(f"  Pressão: {sb.get('pressure', 0)} -> {sa.get('pressure', 0)} ({dp:+}) | Paciência: {sb.get('patience', 0)} -> {sa.get('patience', 0)} ({dpat:+})")
        
        broken = effects.get("newly_broken_claims")
        if broken:
            print(f"  Mentiras Quebradas: {broken}")
        secrets = effects.get("revealed_secrets")
        if secrets:
            print(f"  Segredos Revelados: {secrets}")

        print(f"  NPC: \"{t.npc_text}\"")
        print(f"  IA: Modo={t.response_mode} | Latência={ai_data.get('latency_ms')}ms | Guard Bloqueou={ai_data.get('guard_blocked')}")
    print("=" * 75 + "\n")


def export_turns_to_csv(db, output_file: str):
    turns = db.query(TurnLogModel).order_by(TurnLogModel.id.asc()).all()
    if not turns:
        print("Nenhum turno para exportar.")
        return

    fieldnames = [
        "id", "session_id", "suspect_id", "turn_number", "created_at",
        "player_text", "npc_text", "evidence_id", "intent", "move_type",
        "primary_topic_id", "analysis_provider", "evidence_effect", "response_mode",
        "latency_ms", "guard_blocked", "pressure_before", "pressure_after",
        "patience_before", "patience_after"
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in turns:
            sb = t.state_before or {}
            sa = t.state_after or {}
            ai_data = t.ai or {}
            writer.writerow({
                "id": t.id,
                "session_id": t.session_id,
                "suspect_id": t.suspect_id,
                "turn_number": t.turn_number,
                "created_at": str(t.created_at),
                "player_text": t.player_text,
                "npc_text": t.npc_text,
                "evidence_id": t.evidence_id,
                "intent": t.intent,
                "move_type": t.move_type,
                "primary_topic_id": t.primary_topic_id,
                "analysis_provider": t.analysis_provider,
                "evidence_effect": t.evidence_effect,
                "response_mode": t.response_mode,
                "latency_ms": ai_data.get("latency_ms"),
                "guard_blocked": ai_data.get("guard_blocked"),
                "pressure_before": sb.get("pressure"),
                "pressure_after": sa.get("pressure"),
                "patience_before": sb.get("patience"),
                "patience_after": sa.get("patience"),
            })

    print(f"Exportados {len(turns)} turnos com sucesso para {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Inspecionar logs do Detective AI")
    parser.add_argument("--sessions", action="store_true", help="Lista as sessões existentes")
    parser.add_argument("--session", type=int, help="Mostra o detalhamento de uma sessão")
    parser.add_argument("--export-csv", type=str, help="Exporta turn_logs para arquivo CSV")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.sessions:
            list_sessions(db)
        elif args.session:
            show_session_details(db, args.session)
        elif args.export_csv:
            export_turns_to_csv(db, args.export_csv)
        else:
            list_sessions(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
