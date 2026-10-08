"""
scripts/test_dialogue_flow_validation.py

Simulação prática do fluxo do diálogo relatado pelo jogador, verificando:
1. Reconhecimento dos aliases naturais/plurais nos tópicos sem cair em 'pergunta vaga'.
2. Anti-repetição em follow-ups (evitando papaguear listas repetidas).
3. Suavização e síntese na admissão do Turno 6 (sem dumping monolítico forçado).
"""

import os
import sys

# Garantir UTF-8 no console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Adicionar root do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    NpcChatMessageModel
)
from app.services.session_service import create_session
from app.services.interrogation_turn_service import run_interrogation_turn


def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def run_flow_test():
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(ScenarioModel.scenario_code == "piloto-01").first()
        if not scenario:
            print("[ERRO] Cenário piloto-01 não encontrado.")
            return

        marina = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.suspect_code == "marina_souza"
        ).first()

        evidence = db.query(EvidenceModel).filter(
            EvidenceModel.scenario_id == scenario.id,
            EvidenceModel.evidence_code == "relatorio_contabil"
        ).first()

        session_obj = create_session(scenario.id, db=db)
        session_id = session_obj["id"] if isinstance(session_obj, dict) else session_obj.id

        print_separator(f"TESTE PRÁTICO DO FLUXO DO DIÁLOGO — Sessão #{session_id}")

        turnos = [
            ("Certo, o que você fazia lá?", None, "Pergunta sobre trabalho/rotina"),
            ("Que tipo de relatórios?", None, "Pergunta de follow-up sobre relatórios (plural)"),
            ("Algo que eu preciso ver nos relatórios contábeis?", None, "Follow-up sobre relatórios contábeis"),
            ("Certo. Tenho aqui um relatório contábil que foi claramente alterado. O que sabe sobre isso?", evidence.id, "Apresentação da Evidência e Quebra de Claim"),
        ]

        for i, (text, ev_id, desc) in enumerate(turnos, start=1):
            print_separator(f"TURNO {i}: {desc}")
            print(f"DETETIVE: \"{text}\"")

            res = run_interrogation_turn(
                session_id=session_id,
                suspect_id=marina.id,
                text=text,
                evidence_id=ev_id,
                db=db
            )
            db.commit()

            last_npc_msg = db.query(NpcChatMessageModel).filter(
                NpcChatMessageModel.session_id == session_id,
                NpcChatMessageModel.suspect_id == marina.id,
                NpcChatMessageModel.sender_type == "npc"
            ).order_by(NpcChatMessageModel.id.desc()).first()

            print(f"\nMARINA SOUZA: \"{last_npc_msg.text}\"")
            fb = res.get("narrative_feedback")
            print(f"\n[FEEDBACK UX] Mechanical Effect: {res.get('mechanical_effect')} | Guidance: {fb.get('guidance') if fb else None}")
            if res.get("newly_broken_claims"):
                print(f"[CONQUISTA] Contradições Quebradas: {[c['claim_id'] for c in res['newly_broken_claims']]}")

        print_separator("FIM DO TESTE DE FLUXO")

    finally:
        db.close()


if __name__ == "__main__":
    run_flow_test()
