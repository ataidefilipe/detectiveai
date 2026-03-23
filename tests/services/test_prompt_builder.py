import pytest
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode
from app.services.prompt_builder import build_npc_prompt

def test_build_npc_prompt_injects_new_context():
    """
    Tests if backstory, initial_statement, and final_phrase are properly injected.
    """
    # 1. Arrange
    npc_context = {
        "case": {
            "title": "Test Case",
            "description": "A public story describing the crime.",
            "summary": "Short summary."
        },
        "suspect": {
            "id": 1,
            "name": "John Doe",
            "personality": "Arrogant and defensive.",
            "backstory": "Grew up in the slums, hates the police.",
            "initial_statement": "I was at home watching TV.",
            "final_phrase": "You will never prove anything!",
            "is_closed": False,
            "progress": 0.5
        },
        "revealed_secrets": [],
        "revealed_knowledge": [],
        "broken_claims": [],
        "pressure_points": [],
        "rules": {}
    }

    render_context = NpcResponseRenderContext(
        npc_stance="hostile",
        response_mode=ResponseMode.final_phrase,
        new_secrets_this_turn=[],
        new_knowledge_this_turn=[],
        broken_lies_this_turn=[],
        effectiveness=1.0,
        motive_score=0.0
    )

    chat_history = [
        {"sender": "user", "text": "Are you guilty?"}
    ]

    # 2. Act
    messages = build_npc_prompt(npc_context, chat_history, render_context)

    # 3. Assert
    assert len(messages) == 2 # System + User
    sys_prompt = messages[0]["content"]

    # Check injections
    assert "História Pessoal / Backstory: Grew up in the slums, hates the police." in sys_prompt
    assert "Sua Declaração Inicial: I was at home watching TV." in sys_prompt
    assert "Responda APENAS E EXATAMENTE a sua Frase Final: 'You will never prove anything!'" in sys_prompt
    assert "Nome: John Doe" in sys_prompt
    
    # Check default fallbacks if missing
    npc_context_missing = {
        "case": {"description": "Story"},
        "suspect": {"name": "Jane", "personality": "Shy"}
    }
    render_context.response_mode = ResponseMode.neutral_answer
    
    msgs2 = build_npc_prompt(npc_context_missing, [], render_context)
    sys2 = msgs2[0]["content"]
    assert "História Pessoal / Backstory: Desconhecido." in sys2
    assert "Sua Declaração Inicial: Nada declarado." in sys2
