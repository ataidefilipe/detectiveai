from typing import Dict, Any, List


def build_npc_prompt(
    suspect_state: Dict[str, Any],
    chat_history: List[Dict[str, Any]],
    player_message: Dict[str, Any]
) -> List[dict]:
    """
    Builds a controlled prompt for NPC interaction.

    Rules enforced:
    - NPC can ONLY reference revealed secrets
    - NPC must NOT invent facts
    - NPC must stay in character
    """

    system_prompt = f"""
Você é um personagem de um jogo investigativo.

REGRAS ABSOLUTAS:
- Você NÃO pode inventar fatos
- Você NÃO pode revelar segredos não informados abaixo
- Se não souber algo, diga que não sabe
- Se estiver "fechado", responda apenas com a frase final

PERSONAGEM:
Nome: {suspect_state.get("name")}
Personalidade: {suspect_state.get("personality", "neutra")}

STATUS:
Encerrado: {suspect_state.get("is_closed")}

SEGREDOS REVELADOS (ÚNICAS informações sensíveis permitidas):
{[s["content"] for s in suspect_state.get("revealed_secrets", [])]}
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    # Histórico resumido
    for msg in chat_history[-10:]:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    # Mensagem atual do jogador
    messages.append(
        {
            "role": "user",
            "content": player_message["text"]
        }
    )

    return messages
