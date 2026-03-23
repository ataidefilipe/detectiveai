from app.api.schemas.render_context import NpcResponseRenderContext

def build_npc_prompt(
    npc_context,
    chat_history,
    render_context: NpcResponseRenderContext
):
    
    # 1. Format Allowed Facts and Knowledge
    all_secrets = npc_context.get("revealed_secrets", [])
    allowed_facts_str = "\n".join(f"- {s['content']}" for s in all_secrets) \
        if all_secrets else "Nenhum segredo revelado até agora."
        
    all_knowledge = npc_context.get("revealed_knowledge", [])
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
- NUNCA invente fatos novos.
- NUNCA revele fatos que não estão listados como mandatórios ou já revelados.
- Se o detetive perguntar de algo não listado, seja evasivo ou negue.
- Se a Instrução de Tom exigir a sua Frase Final, retorne apenas ela e encerre.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-10:]:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages

