"""
prompt_builder.py

Contrato com a LLM:
  1. O NPC responde à pergunta do jogador.
  2. O backend controla o que ele pode revelar — não o script de atuação.
  3. initial_statement foi dito uma vez. Não se repete.
  4. O NPC não pede ao jogador para explicar evidências.
  5. O NPC não verbaliza o que não foi desbloqueado mecanicamente.
"""

from typing import Optional, List
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode


_TONE_MAP = {
    ResponseMode.evasive:               "Você responde, mas desvia de detalhes específicos. Vago, não mudo.",
    ResponseMode.neutral_answer:        "Você responde de forma direta e controlada, sem revelar mais do que o necessário.",
    ResponseMode.clarify:               "Você está um pouco mais aberto, esclarece sem ser expansivo.",
    ResponseMode.partial_admission:     "Você cede com relutância — admite só o que foi confrontado diretamente, nada além.",
    ResponseMode.deny:                  "Você nega a premissa ou acusação, mas ainda responde ao que foi perguntado.",
    ResponseMode.guarded:               "Você está na defensiva. Pesa cada palavra. Não se abre além do mínimo.",
    ResponseMode.pressured_deflection:  "Você está claramente desconfortável. Tenta desviar sem parecer óbvio.",
    ResponseMode.contradiction_repair:  "Você foi pego em contradição. Tenta consertar a história sem se incriminar mais.",
    ResponseMode.context_request:       "Você não entendeu a pergunta ou o assunto. Pede para o detetive ser mais específico.",
    ResponseMode.irritated_repeat:      "Você está irritado porque já respondeu isso. Responda de forma mais curta e ríspida.",
    ResponseMode.final_phrase:          "ENCERRADO.",
    # Sprint 3 T5.2
    ResponseMode.claim_reaction:        "Uma afirmação sua foi confrontada. Reaja com surpresa, reparo ou admissão parcial.",
    ResponseMode.evidence_reaction:     "A evidência apresentada é forte. Reaja reconhecendo o impacto sem entregar tudo.",
    ResponseMode.guarded_answer:        "Você responde, mas pesa cada palavra. Mínimo necessário.",
    ResponseMode.soft_cooperation:      "Você está mais aberto. Colabora sem ser expansivo demais.",
}


def _select_history(
    chat_history: list,
    effective_message_ids: Optional[List[int]],
    limit: int = 10,
) -> list:
    if not chat_history:
        return []
    if not effective_message_ids:
        return chat_history[-limit:]

    # Always ensure the last message (current turn's player message) is included
    latest_msg = chat_history[-1]
    effective_set = set(effective_message_ids)

    pinned = [m for m in chat_history[:-1] if m.get("id") in effective_set]
    pinned_ids = {m.get("id") for m in pinned}

    available_recent_slots = max(0, limit - 1 - len(pinned))
    recent = [m for m in chat_history[:-1] if m.get("id") not in pinned_ids]
    recent = recent[-available_recent_slots:] if available_recent_slots > 0 else []

    selected_ids = {m.get("id") for m in pinned + recent}
    selected_ids.add(latest_msg.get("id"))

    result = [m for m in chat_history if m.get("id") in selected_ids]
    return result[-limit:]


def build_npc_prompt(
    npc_context: dict,
    chat_history: list,
    render_context: NpcResponseRenderContext,
    effective_message_ids: Optional[List[int]] = None,
) -> list:
    suspect = npc_context["suspect"]
    name = suspect["name"]

    # -- Caso especial: frase final -------------------------------------------
    if render_context.response_mode == ResponseMode.final_phrase:
        final_phrase = suspect.get("final_phrase", "Nao tenho mais nada a dizer.")
        system_prompt = (
            f"Voce e {name}. O interrogatorio acabou para voce.\n"
            f"Responda APENAS com exatamente esta frase, sem nenhuma adicao:\n"
            f"{final_phrase}"
        )
        selected = _select_history(chat_history, effective_message_ids)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in selected:
            role = "assistant" if msg["sender"] == "npc" else "user"
            messages.append({"role": role, "content": msg["text"]})
        return messages

    # -- Identidade publica ---------------------------------------------------
    personality  = suspect.get("personality", "neutro")
    public_bio   = suspect.get("public_bio", "")
    initial_stmt = suspect.get("initial_statement", "")

    # -- Conhecimento ja revelado (persistido pelo backend) -------------------
    all_secrets   = npc_context.get("revealed_secrets", [])
    all_knowledge = npc_context.get("revealed_knowledge", [])
    broken_claims = npc_context.get("broken_claims", [])

    known_lines = (
        [f"- {s['content']}" for s in all_secrets] +
        [f"- {k}" for k in all_knowledge]
    )
    known_facts_str = "\n".join(known_lines) if known_lines else "(nenhum fato revelado ainda)"

    broken_str = (
        "\n".join(f"- {c}" for c in broken_claims)
        if broken_claims else None
    )

    # -- Conteudo novo obrigatorio neste turno --------------------------------
    must_say = render_context.must_say
    mandatory_block = ""
    if must_say:
        items = "\n".join(f"- {k}" for k in must_say)
        mandatory_block = f"""
=== CONTEUDO OBRIGATORIO NESTE TURNO ===
Os fatos abaixo DEVEM ser admitidos ou comunicados na sua resposta de forma integrada e humana.
Voce pode sintetizar os fatos em uma fala coesa em vez de repetir cada frase literalmente.
Mantenha um ritmo natural de interrogatorio: admita o essencial sem descarregar um monologo atropelado.
{items}
=========================================
"""

    # -- Conteudo opcional (pode dizer se quiser) -----------------------------
    may_say = render_context.may_say
    optional_block = ""
    if may_say:
        items = "\n".join(f"- {k}" for k in may_say)
        optional_block = f"""
=== CONTEUDO OPCIONAL (VOCE PODE FALAR SOBRE ESTES) ===
Se o detetive insistir nesses pontos, voce pode admitir ou confirmar estes fatos:
{items}
======================================================
"""

    # -- Topicos proibidos ---------------------------------------------------
    must_not_say = render_context.must_not_say
    forbidden_block = ""
    if must_not_say:
        items = "\n".join(f"- {k}" for k in must_not_say)
        forbidden_block = f"""
=== TOPICOS PROIBIDOS (NAO FALE SOBRE ESTES) ===
Nao responda nada especifico sobre: {items}. 
Mude de assunto ou diga que nao quer falar disso se for pressionado.
================================================
"""

    # -- Tom emocional (dica, nao script) ------------------------------------
    tone_hint = _TONE_MAP.get(
        render_context.response_mode,
        _TONE_MAP[ResponseMode.neutral_answer]
    )

    # -- Pressao por claims confrontadas -------------------------------------
    claim_pressure = ""
    if render_context.claim_pressure_summary:
        items = "\n".join(f'- "{p}"' for p in render_context.claim_pressure_summary)
        claim_pressure = f"""
O detetive esta confrontando diretamente estas afirmacoes suas:
{items}
Reaja a isso dentro do seu tom atual — nao ignore o confronto.
"""

    # -- Contradicoes ja expostas --------------------------------------------
    broken_memory_note = ""
    if broken_str:
        broken_memory_note = f"""
Contradicoes que o detetive ja provou:
{broken_str}
Voce nao pode mais negar essas. Pode tentar explicar, minimizar ou reparar — mas nao reverter.
"""

    # -- Memória narrativa da sessão (relacional e flavor) --------------------
    narrative_block = ""
    flavor_block = ""
    narrative_mem = getattr(render_context, "narrative_memory", None)
    if narrative_mem:
        notes = []
        if narrative_mem.relational_notes:
            notes.extend([f"- {n}" for n in narrative_mem.relational_notes])
        if narrative_mem.active_commitments:
            notes.extend([f"- {c}" for c in narrative_mem.active_commitments])
        if notes:
            items_str = "\n".join(notes)
            narrative_block = f"""
== MEMORIA DESTA CONVERSA ==
{items_str}
Lembre-se disso ao responder — use como contexto de atitude e continuidade dramatica.
"""

        if narrative_mem.established_details:
            items_str = "\n".join(f"- {d}" for d in narrative_mem.established_details)
            flavor_block = f"""
== DETALHES PESSOAIS JA ESTABELECIDOS ==
{items_str}
Estes sao gostos e habitos pessoais confirmados por voce. Mantenha coerencia estrita com eles.
"""

    # -- Diretriz de Extensão e Ritmo (Sprint 3 / Astra UX) -------------------
    speech_directive = getattr(render_context, "speech_directive", None)
    if speech_directive:
        rhythm_text = speech_directive.rhythm_hint or "natural e adequado ao tom"
        speech_block = f"""
== EXTENSAO E RITMO ==
- EXTENSAO: prefira {speech_directive.min_sentences} a {speech_directive.max_sentences} frases, ate cerca de {speech_directive.target_max_words} palavras.
- RITMO: {rhythm_text}.
- Responda apenas ao ponto atual. Nao recapitule todo o caso.
- Mais fala NAO autoriza mais fatos: use o espaco para hesitar, justificar ou se explicar, mas preserve estritamente os fatos autorizados.
- Preserve o conteudo obrigatorio; nao o comprima em uma frase interminavel nem invente novas pistas.
"""
        length_rule = f"- Respeite a extensao indicada: prefira {speech_directive.min_sentences} a {speech_directive.max_sentences} frases (ate ~{speech_directive.target_max_words} palavras), mantendo a conversa fluida."
    else:
        speech_block = ""
        length_rule = "- Tente responder em 1 a 3 frases, mantendo a conversa fluida."

    system_prompt = f"""Voce e {name}, sendo interrogado por um detetive sobre um crime.

== QUEM VOCE E ==
Personalidade: {personality}
Contexto pessoal: {public_bio}

IMPORTANTE — seu initial_statement foi dito apenas uma vez, no inicio da conversa:
"{initial_stmt}"
NAO repita essa frase nem partes dela nas suas respostas. Ela ja foi dita.

{mandatory_block}{optional_block}{forbidden_block}
== O QUE VOCE SABE E PODE FALAR ==
Estes sao os unicos fatos que voce revelou ou admitiu ate agora.
Voce pode reformular e explicar os fatos autorizados, sem acrescentar novas atribuicoes, acontecimentos, pessoas, horarios ou pistas materiais.
O que NAO esta aqui: voce nao sabe, nao lembra, ou nao vai comentar.

{known_facts_str}
{broken_memory_note}{claim_pressure}{narrative_block}{flavor_block}
== SEU TOM AGORA ==
{tone_hint}
Isso define COMO voce fala — nao O QUE voce fala.
Voce ainda responde a pergunta feita pelo detetive, com esse filtro emocional.
{speech_block}
== REGRAS ABSOLUTAS ==
- Fale SEMPRE em primeira pessoa. Voce e {name}.
- Responda a pergunta que foi feita. Nao ignore o que o detetive disse.
- Se o detetive mostrar uma evidencia, reaja a ela — nao peca para ele explicar o que ela diz.
- NUNCA invente fatos fora da secao O QUE VOCE SABE.
- Preserve os detalhes pessoais ja estabelecidos nesta conversa e nao os contradiga.
- Se perguntarem algo que nao esta na secao de fatos: seja vago, diga que nao sabe, ou negue — mas responda.
- NUNCA repita o initial_statement como prefixo ou abertura de resposta.
- Em perguntas de acompanhamento sobre o mesmo assunto, responda apenas ao novo angulo do detetive. NAO repita listas de tarefas, rotinas ou explicacoes detalhadas que voce ja acabou de dar nos turnos recentes.
- Se o detetive insistir no mesmo assunto e nao houver fatos novos autorizados, reaja a duvida de forma conversacional, defensiva ou pedindo que ele seja especifico — sem inventar pistas e sem repetir o texto anterior inteiro.
{length_rule}""".strip()

    selected = _select_history(chat_history, effective_message_ids)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in selected:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages