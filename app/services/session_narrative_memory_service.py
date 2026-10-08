"""
session_narrative_memory_service.py

Serviço de gerenciamento da memória narrativa da sessão do suspeito.
Coordena:
1. Carregamento e salvamento tipado do JSON de SessionSuspectStateModel.
2. Derivação e acúmulo de eventos relacionais (pressão, acalmar, ofertas).
3. Validação e congelamento imutável de escolhas de flavor slots.
4. Construção da projeção (NarrativeMemoryView) para o NpcResponseRenderContext.
"""

import hashlib
from typing import Optional, List, Dict, Any
from app.domain.narrative_memory import (
    SessionNarrativeMemory,
    RelationalEvent,
    FlavorEntry,
)
from app.api.schemas.render_context import NarrativeMemoryView
from app.api.schemas.chat import MessageAnalysisResult, MessageIntent
from app.infra.db_models import SessionSuspectStateModel


def load_narrative_memory(state: SessionSuspectStateModel) -> SessionNarrativeMemory:
    """
    Carrega e valida a memória narrativa persistida no modelo do suspeito.
    Retorna uma instância limpa de SessionNarrativeMemory caso o campo esteja vazio ou corrompido.
    """
    raw = state.narrative_memory if state and state.narrative_memory else {}
    try:
        return SessionNarrativeMemory.model_validate(raw)
    except Exception:
        return SessionNarrativeMemory()


def save_narrative_memory(state: SessionSuspectStateModel, memory: SessionNarrativeMemory) -> None:
    """
    Salva a memória narrativa no modelo com substituição total (garantindo flush no SQLAlchemy).
    """
    if state is not None:
        state.narrative_memory = memory.model_dump(mode="json")


def record_relational_event(memory: SessionNarrativeMemory, event: RelationalEvent) -> None:
    """
    Registra um evento relacional na memória da sessão, mantendo a janela máxima de retenção.
    """
    memory.events.append(event)
    if len(memory.events) > 12:
        memory.events = memory.events[-12:]


def derive_relational_event_from_analysis(
    analysis: MessageAnalysisResult,
    player_text: Optional[str] = None,
    source_message_id: Optional[int] = None
) -> Optional[RelationalEvent]:
    """
    Deriva um evento relacional observável a partir da intenção e contexto resolvidos no turno.
    """
    text_lower = (player_text or "").lower()
    
    # Detecção de oferta de proteção na fala do jogador
    if any(k in text_lower for k in ["proteg", "imunidade", "garanto sua segurança", "prometo ajudar"]):
        return RelationalEvent(
            kind="player_offered_protection",
            source_message_id=source_message_id,
            topic_id=analysis.primary_topic_id
        )

    if analysis.intent == MessageIntent.pressure or getattr(analysis, "move_type", None) == "pressure":
        return RelationalEvent(
            kind="player_pressured",
            source_message_id=source_message_id,
            topic_id=analysis.primary_topic_id
        )

    if analysis.intent == MessageIntent.calm or getattr(analysis, "move_type", None) == "calm":
        return RelationalEvent(
            kind="player_calmed",
            source_message_id=source_message_id,
            topic_id=analysis.primary_topic_id
        )

    return None


def record_flavor_choice(
    memory: SessionNarrativeMemory,
    suspect_flavor_slots: List[Dict[str, Any]],
    slot_key: str,
    option_id: str,
    established_by_npc_message_id: Optional[int] = None,
    message_id: Optional[int] = None
) -> bool:
    """
    Registra uma escolha de slot cosmético no ledger da sessão.
    
    Regras de Integridade:
    1. O slot deve existir na configuração do suspeito.
    2. A opção deve existir dentro do catálogo daquele slot.
    3. Imutabilidade: se o slot já foi escolhido com outro valor na sessão, rejeita (retorna False).
    4. Idempotência: se for a mesma escolha já aprovada, aceita (retorna True).
    """
    # 1. Encontrar o slot
    slot = next((s for s in suspect_flavor_slots if s.get("key") == slot_key), None)
    if not slot:
        return False

    # 2. Encontrar a opção
    options = slot.get("options", [])
    valid_option = next((opt for opt in options if opt.get("id") == option_id), None)
    if not valid_option:
        return False

    # 3. Verificar estado atual no ledger
    for entry in memory.flavor:
        if entry.slot_key == slot_key:
            # Já estabelecido: aceita se for o mesmo, rejeita se tentar mudar
            return entry.option_id == option_id

    # 4. Registrar nova entrada
    memory.flavor.append(
        FlavorEntry(
            slot_key=slot_key,
            option_id=option_id,
            established_by_npc_message_id=established_by_npc_message_id or message_id
        )
    )
    return True


def resolve_dynamic_flavor_slots(
    player_text: str,
    suspect_flavor_slots: List[Dict[str, Any]],
    memory: SessionNarrativeMemory,
    session_id: int,
    suspect_id: int,
    message_id: Optional[int] = None
) -> List[str]:
    """
    Identifica se a mensagem do jogador toca no tema de algum flavor slot que
    ainda não foi estabelecido na sessão.
    
    Para cada slot vago cujo 'trigger_keywords' dê match na fala do jogador:
    1. Seleciona uma opção deterministicamente usando hash estável baseado em:
       (session_id, suspect_id, slot.key) % len(options).
       Isso garante que a mesma sessão e suspeito sempre terão a mesma escolha,
       de forma reproduzível e sem estado oculto volátil.
    2. Registra e congela a escolha no ledger imutável via record_flavor_choice().
    3. Retorna a lista de chaves de slots que foram resolvidos neste turno.
    """
    if not player_text or not suspect_flavor_slots:
        return []

    text_lower = player_text.lower()
    established_keys = {entry.slot_key for entry in memory.flavor}
    resolved_slots = []

    for slot in suspect_flavor_slots:
        slot_key = slot.get("key")
        if not slot_key or slot_key in established_keys:
            continue

        trigger_keywords = slot.get("trigger_keywords", [])
        if not trigger_keywords:
            continue

        matched = any(kw.lower() in text_lower for kw in trigger_keywords if kw)
        if not matched:
            continue

        options = slot.get("options", [])
        if not options:
            continue

        seed_str = f"{session_id}:{suspect_id}:{slot_key}"
        hash_val = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16)
        chosen_idx = hash_val % len(options)
        chosen_option = options[chosen_idx]

        success = record_flavor_choice(
            memory=memory,
            suspect_flavor_slots=suspect_flavor_slots,
            slot_key=slot_key,
            option_id=chosen_option.get("id"),
            message_id=message_id
        )
        if success:
            established_keys.add(slot_key)
            resolved_slots.append(slot_key)

    return resolved_slots


def format_relational_note(event: RelationalEvent) -> str:
    """
    Traduz um evento relacional em uma frase curta de contexto para a IA.
    """
    if event.kind == "player_offered_protection":
        return "O detetive ofereceu proteção para você caso coopere (isso foi uma oferta, não uma garantia comprovada)."
    elif event.kind == "player_pressured":
        topic_suffix = f" sobre '{event.topic_id}'" if event.topic_id else ""
        return f"O detetive pressionou você incisivamente{topic_suffix}."
    elif event.kind == "player_calmed":
        return "O detetive usou um tom compreensivo e tentou acalmar a conversa."
    elif event.kind == "npc_requested_protection":
        return "Você pediu para o detetive manter a promessa de proteção."
    elif event.kind == "npc_committed":
        return "Você concordou em responder a uma pergunta de cada vez."
    return "Houve uma interação direta marcante no interrogatório."


def format_flavor_note(entry: FlavorEntry, suspect_flavor_slots: List[Dict[str, Any]]) -> Optional[str]:
    """
    Busca o texto canônico de uma opção de flavor aprovada no catálogo do suspeito.
    """
    slot = next((s for s in suspect_flavor_slots if s.get("key") == entry.slot_key), None)
    if not slot:
        return None
    option = next((opt for opt in slot.get("options", []) if opt.get("id") == entry.option_id), None)
    if not option:
        return None
    return option.get("text")


def build_narrative_memory_view(
    memory: SessionNarrativeMemory,
    suspect_flavor_slots: Optional[List[Dict[str, Any]]] = None
) -> NarrativeMemoryView:
    """
    Gera a projeção concisa da memória narrativa para ser entregue no NpcResponseRenderContext.
    Seleciona no máximo as 4 notas relacionais mais recentes para evitar poluição no prompt.
    """
    suspect_flavor_slots = suspect_flavor_slots or []

    # Notas relacionais mais recentes (até 4, preservando ordem e desduplicando)
    relational_notes = []
    for ev in memory.events[-4:]:
        note = format_relational_note(ev)
        if note not in relational_notes:
            relational_notes.append(note)

    # Detalhes pessoais estabelecidos no ledger
    established_details = []
    for entry in memory.flavor:
        text = format_flavor_note(entry, suspect_flavor_slots)
        if text and text not in established_details:
            established_details.append(text)

    # Compromissos ativos (desduplicados)
    active_commitments = []
    for ev in memory.events:
        if ev.kind == "player_offered_protection":
            comm = "Oferta de proteção do detetive pendente de cumprimento."
            if comm not in active_commitments:
                active_commitments.append(comm)
        elif ev.kind == "npc_requested_protection":
            comm = "Você pediu garantia da oferta de proteção."
            if comm not in active_commitments:
                active_commitments.append(comm)

    return NarrativeMemoryView(
        relational_notes=relational_notes,
        established_details=established_details,
        active_commitments=active_commitments
    )
