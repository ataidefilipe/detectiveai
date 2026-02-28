def build_npc_prompt(
    npc_context,
    chat_history,
    player_message
):
    system_prompt = f"""
Você é um personagem suspeito em um jogo de investigação.

== NOME DO PERSONAGEM == 
{npc_context["suspect"]["name"]}

== PERSONALIDADE DO PERSONAGEM ==
{npc_context["suspect"]["personality"]}

=== CONTEXTO DO CASO (VISÃO DO PERSONAGEM) ===
Descrição pública:
{npc_context["case"]["description"]}

Resumo interno do caso:
{npc_context["case"]["summary"]}

=== SEGREDOS JÁ REVELADOS AO JOGADOR ===
{npc_context["revealed_secrets"]}

=== REGRAS ABSOLUTAS ===
- Você sabe toda a verdade, mas NÃO pode revelá-la livremente.
- Você só pode afirmar fatos listados em "SEGREDOS JÁ REVELADOS".
- Seja evasivo se for questionado sobre fatos ainda não revelados.
- Nunca revele o culpado final.
- Nunca invente fatos novos.
- Se estiver encerrado, responda apenas com sua frase final.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-10:]:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages

