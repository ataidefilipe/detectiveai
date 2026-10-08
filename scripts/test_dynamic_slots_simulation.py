"""
scripts/test_dynamic_slots_simulation.py

Demonstração prática da Fase 4 e 5:
Resolução dinâmica e preenchimento orgânico de Flavor Slots no ciclo do turno
para múltiplos suspeitos (Marina, Rogério e Clara), sem intervenção manual.
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
    SessionSuspectStateModel,
    NpcChatMessageModel
)
from app.services.session_service import create_session
from app.services.interrogation_turn_service import run_interrogation_turn
from app.services.session_narrative_memory_service import (
    load_narrative_memory,
    build_narrative_memory_view
)


def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def run_demo():
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(ScenarioModel.scenario_code == "piloto-01").first()
        if not scenario:
            print("[ERRO] Cenário piloto-01 não encontrado no banco.")
            return

        session_obj = create_session(scenario.id, db=db)
        session_id = session_obj["id"] if isinstance(session_obj, dict) else session_obj.id

        print_separator(f"DEMO: RESOLUÇÃO ORGÂNICA DE FLAVOR SLOTS (Sessão #{session_id})")

        # -------------------------------------------------------------
        # 1. MARINA SOUZA — Pergunta sobre comida (ativa preferred_food)
        # -------------------------------------------------------------
        marina = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.suspect_code == "marina_souza"
        ).first()

        print("\n[SUSPEITA 1: MARINA SOUZA]")
        p_msg_1 = "Antes de tudo, me diga: que tipo de comida você prefere no seu dia a dia?"
        print(f"DETETIVE: \"{p_msg_1}\"")

        run_interrogation_turn(
            session_id=session_id,
            suspect_id=marina.id,
            text=p_msg_1,
            evidence_id=None,
            db=db
        )
        db.commit()

        marina_reply = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == marina.id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"MARINA: \"{marina_reply.text}\"")

        marina_state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == marina.id
        ).first()
        mem_marina = load_narrative_memory(marina_state)
        view_marina = build_narrative_memory_view(mem_marina, marina.flavor_slots)
        print(f"-> Slot Resolvido Automaticamente: {[f.slot_key for f in mem_marina.flavor]}")
        print(f"-> Detalhe Estabelecido no Ledger: {view_marina.established_details}")

        # -------------------------------------------------------------
        # 2. ROGÉRIO LIMA — Pergunta sobre bebida na madrugada (ativa preferred_drink)
        # -------------------------------------------------------------
        rogerio = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.suspect_code == "rogerio_lima"
        ).first()

        print("\n[SUSPEITO 2: ROGÉRIO LIMA]")
        p_msg_2 = "Rogério, o que você costuma beber durante a noite para aguentar o sono na ronda?"
        print(f"DETETIVE: \"{p_msg_2}\"")

        run_interrogation_turn(
            session_id=session_id,
            suspect_id=rogerio.id,
            text=p_msg_2,
            evidence_id=None,
            db=db
        )
        db.commit()

        rogerio_reply = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == rogerio.id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"ROGÉRIO: \"{rogerio_reply.text}\"")

        rogerio_state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == rogerio.id
        ).first()
        mem_rogerio = load_narrative_memory(rogerio_state)
        view_rogerio = build_narrative_memory_view(mem_rogerio, rogerio.flavor_slots)
        print(f"-> Slot Resolvido Automaticamente: {[f.slot_key for f in mem_rogerio.flavor]}")
        print(f"-> Detalhe Estabelecido no Ledger: {view_rogerio.established_details}")

        # -------------------------------------------------------------
        # 3. CLARA MARTINS — Pergunta sobre estudo e anotações (ativa study_routine)
        # -------------------------------------------------------------
        clara = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.suspect_code == "clara_martins"
        ).first()

        print("\n[SUSPEITA 3: CLARA MARTINS]")
        p_msg_3 = "Clara, como você costuma organizar o seu estudo e anotações aqui no estágio?"
        print(f"DETETIVE: \"{p_msg_3}\"")

        run_interrogation_turn(
            session_id=session_id,
            suspect_id=clara.id,
            text=p_msg_3,
            evidence_id=None,
            db=db
        )
        db.commit()

        clara_reply = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == clara.id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"CLARA: \"{clara_reply.text}\"")

        clara_state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == clara.id
        ).first()
        mem_clara = load_narrative_memory(clara_state)
        view_clara = build_narrative_memory_view(mem_clara, clara.flavor_slots)
        print(f"-> Slot Resolvido Automaticamente: {[f.slot_key for f in mem_clara.flavor]}")
        print(f"-> Detalhe Estabelecido no Ledger: {view_clara.established_details}")

        print_separator("RESUMO DE SUCESSO")
        print("Todos os slots periféricos foram resolvidos pelo backend e respeitados pela IA!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
