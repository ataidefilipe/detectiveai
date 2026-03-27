def build_npc_context(
    scenario,
    suspect,
    suspect_state: dict,
    revealed_secrets: list,
    pressure_points: list
) -> dict:
    return {
        "case": {
            "title": scenario.title,
            "description": scenario.description,
            "summary": scenario.case_summary
        },
        "suspect": {
            "id": suspect.id,
            "name": suspect.name,
            "personality": suspect.personality,
            "backstory": suspect.backstory,
            "initial_statement": suspect.initial_statement,
            "final_phrase": suspect.final_phrase,
            "is_closed": suspect_state.get("is_closed", False),
            "progress": suspect_state.get("progress", 0.0),
        },
        # 🔴 CONTROLE DO BACKEND
        "revealed_secrets": revealed_secrets,
        "revealed_knowledge": suspect_state.get("revealed_knowledge", []),
        "broken_claims": suspect_state.get("broken_claims", []),
        "pressure_points": pressure_points,
        "rules": {
            "can_only_use_revealed_secrets": True,
            "never_invent_facts": True,
            "never_reveal_unmarked_information": True,
        }
    }
