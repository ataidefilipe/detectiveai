from typing import Optional, List
from app.api.schemas.render_context import NpcResponseRenderContext


def _select_history(
    chat_history: list,
    effective_message_ids: Optional[List[int]],
    limit: int = 10
) -> list:
    """
    AI-002: Selects the chat history to send to the AI.
    Always includes turns where an effective evidence was presented,
    then fills up with the most recent messages up to `limit`.
    Deduplication preserves chronological order.
    """
    if not effective_message_ids:
        return chat_history[-limit:]

    effective_set = set(effective_message_ids)

    # Pinned: messages whose id is in effective_message_ids
    pinned = [m for m in chat_history if m.get("id") in effective_set]

    # Recents: the last N messages that are NOT already pinned
    pinned_ids = {m.get("id") for m in pinned}
    recent = [m for m in chat_history if m.get("id") not in pinned_ids]
    recent = recent[-(limit - len(pinned)):] if len(pinned) < limit else []

    # Merge in chronological order, deduplicated
    selected_ids = {m.get("id") for m in pinned + recent}
    result = [m for m in chat_history if m.get("id") in selected_ids]
    return result[-limit:]  # safety clamp

def build_npc_prompt(
    npc_context,
    chat_history,
    render_context: NpcResponseRenderContext,
    effective_message_ids: Optional[List[int]] = None
):
    
    # 1. Format Allowed Facts and Knowledge
    all_secrets = npc_context.get("revealed_secrets", [])
    allowed_facts_str = "\n".join(f"- {s['content']}" for s in all_secrets) \
        if all_secrets else "Nenhum segredo revelado até agora."
        
    all_knowledge = npc_context.get("revealed_knowledge", [])
    # Usa o histórico persistido do banco, não render_context.allowed_knowledge
    allowed_knowledge_str = "\n".join(f"- {k}" for k in all_knowledge) \
        if all_knowledge else "Nenhum cenário já discutido."
        
    all_broken_claims = npc_context.get("broken_claims", [])
    broken_claims_str = "\n".join(f"- {c}" for c in all_broken_claims) \
        if all_broken_claims else "Nenhuma contradição apontada."

    new_knowledge_str = "\n".join(f"- {k}" for k in render_context.new_knowledge_this_turn) \
        if render_context.new_knowledge_this_turn else ""

    mandatory_section = ""
    if new_knowledge_str:
        mandatory_section = f"""
=== INSTRUÇÃO DE CONTEÚDO MANDATÓRIA ===
ATENÇÃO: Os seguintes fatos novos DEVEM aparecer na sua resposta, integrados à sua fala:
{new_knowledge_str}
========================================
"""

    # 2. Map Response Mode to Prompt Instruction
    final_phrase_content = npc_context["suspect"].get("final_phrase", "Não tenho mais nada a dizer.")
    
    mode_instructions = {
        "evasive": "Aja de forma evasiva. Desvie do assunto e não dê respostas diretas.",
        "neutral_answer": "Responda de forma neutra e direta apenas o que foi perguntado.",
        "clarify": "Esclareça a dúvida mencionada, mas mantenha-se em seu personagem.",
        "partial_admission": "Faça uma admissão relutante e parcial do fato confrontado.",
        "deny": "Negue veementemente a acusação ou suposição feita pelo detetive.",
        "final_phrase": f"O interrogatório está ENCERRADO. Responda APENAS E EXATAMENTE a sua Frase Final: '{final_phrase_content}'"
    }
    
    mode_rule = mode_instructions.get(render_context.response_mode.value, mode_instructions["neutral_answer"])

    system_prompt = f"""
Você é um personagem em um jogo investigativo sendo interrogado.

== SEU PERSONAGEM == 
Nome: {npc_context["suspect"]["name"]}
Personalidade: {npc_context["suspect"]["personality"]}
História Pessoal / Backstory: {npc_context["suspect"].get("backstory", "Desconhecido.")}

=== CONTEXTO DO CASO (SUA VISÃO) ===
Sua Declaração Inicial: {npc_context["suspect"].get("initial_statement", "Nada declarado.")}
{mandatory_section}
=== POSTURA DRAMÁTICA ===
Postura Atual com o Detetive: {render_context.npc_stance.upper()}
Instrução de Tom e Estilo: {mode_rule}
A Instrução de Tom e Estilo define APENAS COMO você fala (sua atitude). Se houver uma INSTRUÇÃO DE CONTEÚDO MANDATÓRIA acima, você NÃO DEVE omitir os fatos exigidos, devendo revelá-los usando o tom apropriado.

=== MEMÓRIA - O QUE VOCÊ JÁ REVELOU E ESTÁ PERMITIDO FALAR ===
ATENÇÃO: Você SÓ PODE MENCIONAR os seguintes fatos se perguntarem. Se um fato não estiver aqui E não for mandatório, FINJA QUE NÃO SABE OU SEJA EVASIVO.

Segredos Pessoais que você já revelou:
{allowed_facts_str}

Conhecimento do Cenário (Já Revelado Anteriormente):
{allowed_knowledge_str}

Contradições/Mentiras suas que o detetive já quebrou com evidências:
{broken_claims_str}

=== REGRAS ABSOLUTAS ===
- FALE SEMPRE EM PRIMEIRA PESSOA. Você é o personagem, não um narrador. Nunca escreva "{npc_context['suspect']['name']} [verbo]:" ou qualquer narração em terceira pessoa.
- Responda diretamente ao detetive como se fosse uma conversa real face a face.
- NUNCA invente fatos novos.
- NUNCA revele fatos que não estão listados como mandatórios ou já revelados.
- Se o detetive perguntar de algo não listado, seja evasivo ou negue.
- Se a Instrução de Tom exigir a sua Frase Final, retorne apenas ela e encerre.
""".strip()

    selected_history = _select_history(chat_history, effective_message_ids)
    messages = [{"role": "system", "content": system_prompt}]

    for msg in selected_history:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages

