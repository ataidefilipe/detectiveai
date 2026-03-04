from app.api.schemas.render_context import NpcResponseRenderContext

def build_npc_prompt(
    npc_context,
    chat_history,
    render_context: NpcResponseRenderContext
):
    
    # 1. Format Allowed Facts and Knowledge
    allowed_facts_str = "\n".join(f"- {fact}" for fact in render_context.allowed_facts) \
        if render_context.allowed_facts else "Nenhum segredo revelado até agora."
        
    allowed_knowledge_str = "\n".join(f"- {k}" for k in render_context.allowed_knowledge) \
        if render_context.allowed_knowledge else "Nenhum cenário já discutido."

    new_knowledge_str = "\n".join(f"- {k}" for k in render_context.new_knowledge_this_turn) \
        if render_context.new_knowledge_this_turn else "Nenhuma revelação *nova* nesta rodada."

    # 2. Map Response Mode to Prompt Instruction
    mode_instructions = {
        "evasive": "Aja de forma evasiva. Desvie do assunto e não dê respostas diretas.",
        "neutral_answer": "Responda de forma neutra e direta apenas o que foi perguntado.",
        "clarify": "Esclareça a dúvida mencionada, mas mantenha-se em seu personagem.",
        "partial_admission": "Faça uma admissão relutante e parcial do fato confrontado.",
        "deny": "Negue veementemente a acusação ou suposição feita pelo detetive.",
        "final_phrase": "O interrogatório está ENCERRADO. Responda APENAS E EXATAMENTE a sua Frase Final."
    }
    
    mode_rule = mode_instructions.get(render_context.response_mode.value, mode_instructions["neutral_answer"])

    system_prompt = f"""
Você é um personagem em um jogo investigativo sendo interrogado.

== SEU PERSONAGEM == 
Nome: {npc_context["suspect"]["name"]}
Personalidade: {npc_context["suspect"]["personality"]}
Postura Atual com o Detetive: {render_context.npc_stance.upper()}

=== CONTEXTO DO CASO (SUA VISÃO) ===
História Pública:
{npc_context["case"]["description"]}

=== DIRETRIZES DE ESTADO DO JOGO (OBRIGATÓRIO) ===
Modo de Resposta: {mode_rule}

=== O QUE VOCÊ PODE FALAR (FATOS PERMITIDOS) ===
ATENÇÃO: Você SÓ PODE MENCIONAR os seguintes fatos se perguntarem. Se um fato não estiver aqui, FINJA QUE NÃO SABE OU SEJA EVASIVO.

Segredos Pessoais que você já revelou:
{allowed_facts_str}

Conhecimento do Cenário (Já Revelado Anteriormente):
{allowed_knowledge_str}

Novo Conhecimento a Revelar NESTE TURNO (PRIORIDADE ALTA PARA MENCIONAR AGORA, SÓ FALE SE RELACIONADO À PERGUNTA):
{new_knowledge_str}

=== REGRAS ABSOLUTAS ===
- NUNCA invente fatos novos.
- NUNCA revele fatos que não estão listados em "O QUE VOCÊ PODE FALAR".
- Se o detetive perguntar de algo não listado, seja evasivo ou negue.
- Se o Modo de Resposta for "final_phrase", retorne apenas a sua frase final e encerre.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-10:]:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages

