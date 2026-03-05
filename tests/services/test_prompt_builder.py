import pytest
from app.services.prompt_builder import build_npc_prompt
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode

def test_prompt_builder_injects_render_context_correctly():
    # Mock context pieces
    npc_context = {
        "suspect": {"name": "Test Name", "personality": "Test Personality"},
        "case": {"description": "Public Test", "summary": "Secret Test"},
        "revealed_secrets": [{"content": "I like cheese"}, {"content": "I hate cats"}],
        "revealed_knowledge": ["The key is under the mat"]
    }
    chat_history = []
    player_message = {"text": "Hello"}
    
    # Target Context with Evasive restriction
    render_context = NpcResponseRenderContext(
        npc_stance="hostile",
        response_mode=ResponseMode.evasive
    )
    
    # Generate Prompt
    messages = build_npc_prompt(
        npc_context=npc_context,
        chat_history=chat_history,
        render_context=render_context
    )
    
    system_prompt = messages[0]["content"]
    
    # Assertions
    assert "HOSTILE" in system_prompt
    assert "evasiva" in system_prompt.lower()
    
    # Check allowed facts
    assert "I like cheese" in system_prompt
    assert "I hate cats" in system_prompt
    
    # Check allowed knowledge
    assert "The key is under the mat" in system_prompt
    
    # Rules enforcing bounds
    assert "NUNCA invente fatos novos" in system_prompt


def test_prompt_builder_without_facts():
    npc_context = {
        "suspect": {"name": "X", "personality": "Y"},
        "case": {"description": "D", "summary": "S"},
        "revealed_secrets": [],
        "revealed_knowledge": []
    }
    
    render_context = NpcResponseRenderContext(
        npc_stance="neutral",
        response_mode=ResponseMode.neutral_answer
    )
    
    messages = build_npc_prompt(
        npc_context=npc_context,
        chat_history=[],
        render_context=render_context
    )
    
    system_prompt = messages[0]["content"]
    
    # Should contain fallback texts
    assert "Nenhum segredo revelado até agora" in system_prompt
    assert "Nenhum cenário já discutido." in system_prompt
