"""
scripts/test_memory_roleplay_simulation.py

Simulação prática do interrogatório de Marina Souza com a nova arquitetura
de Memória Híbrida e Determinística (Memória Relacional + Flavor Slots).
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
    SessionModel,
    SessionSuspectStateModel,
    NpcChatMessageModel
)
from app.services.session_service import create_session, get_suspect_state
from app.services.interrogation_turn_service import run_interrogation_turn
from app.services.session_narrative_memory_service import (
    load_narrative_memory,
    save_narrative_memory,
    record_flavor_choice,
    build_narrative_memory_view
)
from app.services.prompt_builder import build_npc_prompt
from app.services.npc_context_builder import build_npc_context


def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def run_simulation():
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(ScenarioModel.scenario_code == "piloto-01").first()
        if not scenario:
            print("[ERRO] Cenário piloto-01 não encontrado no banco. Execute reset_dev_db.py primeiro.")
            return

        suspect = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario.id,
            SuspectModel.suspect_code == "marina_souza"
        ).first()
        if not suspect:
            print("[ERRO] Suspeita Marina Souza não encontrada.")
            return

        print_separator("INICIANDO SESSÃO DE INTERROGATÓRIO: MARINA SOUZA")
        session_obj = create_session(scenario.id, db=db)
        session_id = session_obj["id"] if isinstance(session_obj, dict) else session_obj.id
        print(f"[OK] Sessão #{session_id} criada para o caso '{scenario.title}'")
        print(f"[OK] Suspeita: {suspect.name} (ID: {suspect.id})")
        print(f"[OK] Initial Statement: \"{suspect.initial_statement}\"")
        print(f"[OK] Flavor Slots disponíveis: {[s['key'] for s in suspect.flavor_slots]}")

        # Obter estado do suspeito
        suspect_state_model = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect.id
        ).first()

        # =====================================================================
        # TURNO 1: Pergunta periférica de abertura
        # =====================================================================
        print_separator("TURNO 1: PERGUNTA PERIFÉRICA DE ABERTURA")
        player_msg_1 = "Antes de falarmos do Heitor, me diz uma coisa: de que tipo de comida você gosta?"
        print(f"DETETIVE: \"{player_msg_1}\"")

        # Registra a escolha autorada no ledger da sessão (simulando preenchimento de lacuna)
        narrative_mem = load_narrative_memory(suspect_state_model)
        record_flavor_choice(
            memory=narrative_mem,
            suspect_flavor_slots=suspect.flavor_slots,
            slot_key="preferred_food",
            option_id="simple_pasta"
        )
        save_narrative_memory(suspect_state_model, narrative_mem)
        db.commit()

        # Executa o turno
        res_1 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text=player_msg_1,
            evidence_id=None,
            db=db
        )
        db.commit()

        # Resposta do NPC
        last_npc_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"\nMARINA SOUZA: \"{last_npc_msg.text}\"")

        db.refresh(suspect_state_model)
        mem_after_1 = load_narrative_memory(suspect_state_model)
        print(f"\n[BACKEND] Stance: {suspect_state_model.stance} | Patience: {suspect_state_model.patience:.1f} | Pressure: {suspect_state_model.pressure:.1f}")
        print(f"[MEMÓRIA NARRATIVA] Flavor Estabelecido: {[f.option_id for f in mem_after_1.flavor]}")
        print(f"[MEMÓRIA NARRATIVA] Eventos Relacionais: {[e.kind for e in mem_after_1.events]}")

        # =====================================================================
        # TURNO 2: Tentativa de induzir álibi falso
        # =====================================================================
        print_separator("TURNO 2: TENTATIVA DO JOGADOR DE INDUZIR ÁLIBI FALSO")
        player_msg_2 = "Então ontem você almoçou massa com a Clara no restaurante?"
        print(f"DETETIVE: \"{player_msg_2}\"")

        res_2 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text=player_msg_2,
            evidence_id=None,
            db=db
        )
        db.commit()

        last_npc_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"\nMARINA SOUZA: \"{last_npc_msg.text}\"")
        db.refresh(suspect_state_model)
        print(f"\n[BACKEND] Stance: {suspect_state_model.stance} | Patience: {suspect_state_model.patience:.1f} | Pressure: {suspect_state_model.pressure:.1f}")

        # =====================================================================
        # TURNO 3: Oferta de proteção
        # =====================================================================
        print_separator("TURNO 3: OFERTA DE PROTEÇÃO (EMPATIA / ACORDO RELACIONAL)")
        player_msg_3 = "Calma, não precisa ficar na defensiva. Se você cooperar comigo, eu prometo tentar te proteger."
        print(f"DETETIVE: \"{player_msg_3}\"")

        res_3 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text=player_msg_3,
            evidence_id=None,
            db=db
        )
        db.commit()

        last_npc_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"\nMARINA SOUZA: \"{last_npc_msg.text}\"")

        db.refresh(suspect_state_model)
        mem_after_3 = load_narrative_memory(suspect_state_model)
        print(f"\n[BACKEND] Stance: {suspect_state_model.stance} | Patience: {suspect_state_model.patience:.1f} | Pressure: {suspect_state_model.pressure:.1f}")
        print(f"[MEMÓRIA NARRATIVA] Eventos Relacionais Acumulados: {[e.kind for e in mem_after_3.events]}")

        # =====================================================================
        # TURNO 4: Cobrança da promessa e pergunta investigativa
        # =====================================================================
        print_separator("TURNO 4: COBRANÇA DA PROMESSA & PERGUNTA SOBRE O RELATÓRIO")
        player_msg_4 = "Você ainda duvida da minha palavra? Eu prometi tentar te proteger. Agora me conta: o que estava acontecendo com os dados contábeis?"
        print(f"DETETIVE: \"{player_msg_4}\"")

        res_4 = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect.id,
            text=player_msg_4,
            evidence_id=None,
            db=db
        )
        db.commit()

        last_npc_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.sender_type == "npc"
        ).order_by(NpcChatMessageModel.id.desc()).first()

        print(f"\nMARINA SOUZA: \"{last_npc_msg.text}\"")

        db.refresh(suspect_state_model)
        mem_after_4 = load_narrative_memory(suspect_state_model)
        view_4 = build_narrative_memory_view(mem_after_4, suspect.flavor_slots)

        print("\n" + "-" * 70)
        print("  ESTADO FINAL DA MEMÓRIA NARRATIVA NA SESSÃO")
        print("-" * 70)
        print("Notas Relacionais Injetadas no Prompt:")
        for note in view_4.relational_notes:
            print(f"  - {note}")
        print("Detalhes de Flavor Fixados:")
        for det in view_4.established_details:
            print(f"  - {det}")
        print("Compromissos Registrados:")
        for com in view_4.active_commitments:
            print(f"  - {com}")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_simulation()
