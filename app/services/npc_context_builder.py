def build_npc_context(
    scenario,
    suspect,
    suspect_state: dict,
    revealed_secrets: list,
    pressure_points: list,
    true_timeline: list | str,
    lies: list | str
) -> dict:
    return {
        "case": {
            "title": scenario.title,
            "description": scenario.description,
            "summary": scenario.case_summary,
        },
        "suspect": {
            "id": suspect.id,
            "name": suspect.name,
            "backstory": suspect.backstory,
            "final_phrase": suspect.final_phrase,
            "is_closed": suspect_state.get("is_closed", False),
            "progress": suspect_state.get("progress", 0.0),
        },
        # 🔴 APENAS PARA IA
        "true_timeline": true_timeline or "Linha do tempo não definida.",
        "lies": lies or [],
        # 🔴 CONTROLADO PELO BACKEND
        "revealed_secrets": revealed_secrets,
        "pressure_points": pressure_points,
        "rules": {
            "can_only_use_revealed_secrets": True,
            "never_invent_facts": True,
            "never_reveal_unmarked_information": True,
        }
    }
