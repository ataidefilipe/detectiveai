"""
npc_context_builder.py

Constroi o dicionario de contexto enviado para a LLM.

Regra central:
    backstory e case_summary existem para o autor e para o motor mecanico.
    A LLM recebe apenas o que o personagem diria sobre si mesmo em publico —
    nao a sinopse do culpado.
"""


from typing import Optional, Dict, Any, List


def _public_persona(suspect) -> str:
    """
    Extrai a descricao publica do personagem.

    Usa apenas a primeira sentenca do backstory — apresentacao neutra de quem
    ele e profissionalmente. O restante do backstory contem motivacoes, culpa
    e detalhes internos que nao devem ser verbalizados livremente pela LLM.

    O backend controla o que pode ser revelado via knowledge/secrets.
    """
    raw_backstory = suspect.backstory or ""
    first_sentence = raw_backstory.split(".")[0].strip() if raw_backstory else ""
    return first_sentence + "." if first_sentence else ""


def build_npc_context(
    scenario,
    suspect,
    suspect_state: dict,
    revealed_secrets: list,
    pressure_points: list,
    presented_evidence: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Monta o contexto enviado para a LLM.

    O que VAI para a LLM:
      - Identidade publica (nome, cargo resumido — primeira sentenca do backstory)
      - initial_statement (como referencia de tom — nao para repeticao)
      - Segredos ja revelados (persistidos no banco)
      - Knowledge ja revelado (persistido no banco)
      - Claims quebradas (o NPC sabe que foi pego nelas)
      - Titulo e descricao publica do caso

    O que NAO VAI para a LLM:
      - backstory completo (contem motivacao, culpa, linha do tempo interna)
      - case_summary (sinopse interna do crime — spoiler total)
      - internal_note (notas do autor)
      - true_timeline (linha do tempo real do suspeito)
    """
    public_bio = _public_persona(suspect)

    return {
        "case": {
            "title": scenario.title,
            "description": scenario.description,  # descricao publica, nao o case_summary
        },
        "suspect": {
            "id": suspect.id,
            "name": suspect.name,
            "personality": suspect.personality,
            "public_bio": public_bio,
            "initial_statement": suspect.initial_statement or "",
            "final_phrase": suspect.final_phrase or "Nao tenho mais nada a dizer.",
            "is_closed": suspect_state.get("is_closed", False),
        },
        # Tudo abaixo foi desbloqueado mecanicamente pelo backend.
        # A LLM pode verbalizar esses fatos porque o motor disse que pode.
        "revealed_secrets": revealed_secrets,
        "revealed_knowledge": suspect_state.get("revealed_knowledge", []),
        "broken_claims": suspect_state.get("broken_claims", []),
        "active_claims": suspect_state.get("active_claims", []),
        "pressure_points": pressure_points,
        "presented_evidence": presented_evidence,
        "rules": {
            "can_only_use_revealed_secrets": True,
            "never_invent_facts": True,
            "never_reveal_unmarked_information": True,
        },
    }