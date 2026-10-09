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
            "public_bio": "Grew up in the slums.",
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
        response_mode=ResponseMode.neutral_answer,
        new_knowledge_this_turn=[]
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
    assert "Contexto pessoal: Grew up in the slums." in sys_prompt
    assert '"I was at home watching TV."' in sys_prompt
    assert "Voce e John Doe" in sys_prompt
    
    # Check default fallbacks if missing
    npc_context_missing = {
        "case": {"description": "Story"},
        "suspect": {"name": "Jane", "personality": "Shy"}
    }
    render_context.response_mode = ResponseMode.neutral_answer
    
    msgs2 = build_npc_prompt(npc_context_missing, [], render_context)
    sys2 = msgs2[0]["content"]
    assert "Contexto pessoal: " in sys2
    assert '""' in sys2
    
def test_build_npc_prompt_injects_claim_pressure():
    npc_context = {
        "suspect": {"name": "Test", "personality": "Normal"}
    }
    render_context = NpcResponseRenderContext(
        npc_stance="hostile",
        response_mode=ResponseMode.pressured_deflection,
        claim_pressure_summary=["Eu não vi ninguém", "Eu estava no trabalho"]
    )
    
    messages = build_npc_prompt(npc_context, [], render_context)
    sys_prompt = messages[0]["content"]
    
    assert "O detetive esta confrontando diretamente estas afirmacoes suas:" in sys_prompt
    assert "Eu não vi ninguém" in sys_prompt
    assert "Eu estava no trabalho" in sys_prompt

def test_build_npc_prompt_injects_active_claims():
    npc_context = {
        "suspect": {"name": "Marina Souza", "personality": "nervoso"},
        "active_claims": [
            "Eu estava sozinha no meu quarto a noite toda. Nem saí para jantar.",
            "Eu vi as inconsistências no relatório, mas não sei quem fez isso."
        ]
    }
    render_context = NpcResponseRenderContext(
        npc_stance="defensive",
        response_mode=ResponseMode.neutral_answer,
    )
    
    messages = build_npc_prompt(npc_context, [], render_context)
    sys_prompt = messages[0]["content"]
    
    assert "== SUA VERSAO OFICIAL DOS FATOS (SUAS DECLARACOES / ALIBI) ==" in sys_prompt
    assert "Eu estava sozinha no meu quarto a noite toda. Nem saí para jantar." in sys_prompt
    assert "Eu vi as inconsistências no relatório, mas não sei quem fez isso." in sys_prompt
    assert "NUNCA invente fatos fora de SUA VERSAO OFICIAL e da secao O QUE VOCE SABE." in sys_prompt

def test_build_npc_prompt_injects_presented_evidence():
    npc_context = {
        "suspect": {"name": "Marina Souza", "personality": "nervoso"},
        "presented_evidence": {
            "id": 2,
            "name": "Cartão de Acesso de Marina",
            "description": "Registro eletrônico mostra que o cartão de Marina abriu a porta às 22h14."
        }
    }
    render_context = NpcResponseRenderContext(
        npc_stance="defensive",
        response_mode=ResponseMode.neutral_answer,
    )
    
    messages = build_npc_prompt(npc_context, [], render_context)
    sys_prompt = messages[0]["content"]
    
    assert "=== EVIDENCIA APRESENTADA PELO DETETIVE NESTE TURNO ===" in sys_prompt
    assert "Cartão de Acesso de Marina" in sys_prompt
    assert "Registro eletrônico mostra que o cartão de Marina abriu a porta às 22h14." in sys_prompt

def test_build_npc_prompt_no_presented_evidence_omits_block():
    npc_context = {
        "suspect": {"name": "Marina Souza", "personality": "nervoso"},
        "presented_evidence": None
    }
    render_context = NpcResponseRenderContext(
        npc_stance="neutral",
        response_mode=ResponseMode.neutral_answer,
    )
    
    messages = build_npc_prompt(npc_context, [], render_context)
    sys_prompt = messages[0]["content"]
    
    assert "=== EVIDENCIA APRESENTADA PELO DETETIVE NESTE TURNO ===" not in sys_prompt


