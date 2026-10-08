"""
T1.5 — Prompt de classificação semântica.

Separado do código do adapter para facilitar iteração e snapshot testing.
O prompt instrui a IA a classificar a fala do jogador, não a jogar o jogo.
"""
from typing import List, Optional

SYSTEM_PROMPT = """Você é um classificador de mensagens em um jogo de interrogatório policial.

Sua função é analisar a fala do jogador (detetive) e classificá-la em campos estruturados.

REGRAS ABSOLUTAS:
- Classifique a fala do jogador. Não responda como personagem.
- Não determine se o suspeito é culpado.
- Não invente tópicos; escolha APENAS IDs fornecidos na lista de tópicos.
- Não use conhecimento externo ao que foi fornecido.
- Se a fala for ambígua, use confiança baixa (< 0.5).
- Se a fala não se encaixa em nenhum tópico, use primary_topic_id: null e move_type: "off_topic".
- Retorne APENAS o JSON no formato especificado. Sem texto adicional.

CAMPOS PARA RETORNAR:
- primary_topic_id: ID do tópico principal da fala (null se nenhum)
- detected_topic_ids: lista de todos os IDs de tópicos mencionados
- intent: "ask" | "pressure" | "confront" | "accuse" | "calm" | "unknown"
- move_type: tipo de jogada (ver enum abaixo)
- target_claim_ids: IDs de claims que o jogador parece estar confrontando
- referenced_evidence_ids: IDs de evidências mencionadas indiretamente na fala
- confidence: 0.0 a 1.0, quão confiante você está na classificação

MOVE_TYPES:
- "explore": pergunta aberta sobre tópico novo
- "deepen": aprofundamento no mesmo tópico
- "clarify": pedido de esclarecimento
- "pressure": pressão direta / intimidação
- "calm": acalmamento / empatia
- "confront_claim": confrontar uma declaração do suspeito
- "confront_evidence": apresentar evidência contra o suspeito
- "accuse_in_chat": acusação direta na conversa
- "off_topic": fala fora do contexto do caso
- "unknown": não é possível classificar"""


def build_classification_prompt(
    player_text: str,
    topics: List[dict],
    claims: List[dict],
    evidences: List[dict],
    suspect_state: Optional[dict] = None,
    recent_messages: Optional[List[str]] = None,
    active_topic_id: Optional[str] = None,
) -> str:
    """
    Monta o prompt de contexto para o classificador semântico.

    Envia APENAS informação pública — nunca culpado, case_summary,
    segredos ocultos, timeline verdadeira, notas internas ou motivo real.
    """

    # Tópicos públicos
    topics_text = "\n".join(
        f"- id: {t['id']}, label: {t.get('label', t['id'])}, "
        f"sensitive: {t.get('is_sensitive', False)}"
        for t in topics
    ) if topics else "(nenhum tópico definido)"

    # Claims públicas/ativas
    claims_text = "\n".join(
        f"- claim_id: {c.get('claim_id', c.get('id', '?'))}, "
        f"topic: {c.get('topic_id', '?')}, "
        f"text: \"{c.get('text', c.get('public_text', ''))}\""
        for c in claims
    ) if claims else "(nenhuma claim ativa)"

    # Evidências públicas
    evidences_text = "\n".join(
        f"- id: {e.get('id', '?')}, name: {e.get('name', '?')}, "
        f"topic: {e.get('related_topic_id', 'nenhum')}"
        for e in evidences
    ) if evidences else "(nenhuma evidência)"

    # Contexto conversacional
    context_parts = []
    if active_topic_id:
        context_parts.append(f"Tópico ativo na conversa: {active_topic_id}")

    if recent_messages:
        context_parts.append(
            "Últimas falas do jogador:\n" +
            "\n".join(f"  - \"{m}\"" for m in recent_messages[-3:])
        )

    if suspect_state:
        state_items = []
        if "stance" in suspect_state:
            state_items.append(f"postura: {suspect_state['stance']}")
        if "pressure" in suspect_state:
            state_items.append(f"pressão: {suspect_state['pressure']}")
        if "patience" in suspect_state:
            state_items.append(f"paciência: {suspect_state['patience']}")
        if state_items:
            context_parts.append("Estado do suspeito: " + ", ".join(state_items))

    context_text = "\n".join(context_parts) if context_parts else "(sem contexto adicional)"

    return f"""=== TÓPICOS DO CASO ===
{topics_text}

=== CLAIMS DO SUSPEITO ===
{claims_text}

=== EVIDÊNCIAS DISPONÍVEIS ===
{evidences_text}

=== CONTEXTO DA CONVERSA ===
{context_text}

=== FALA DO JOGADOR ===
\"{player_text}\""""
