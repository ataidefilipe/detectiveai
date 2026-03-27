from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode


def test_dummy_adapter_deny():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.deny)
    res = adapter.generate_reply({}, [], {}, rc)
    # First-person: no longer uses name prefix; must deny
    assert "não sei nada" in res.lower()


def test_dummy_adapter_evasive():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.evasive)
    res = adapter.generate_reply({}, [], {}, rc)
    assert "não lembro" in res.lower()


def test_dummy_adapter_clarify():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.clarify, allowed_knowledge=["Fato crucial"])
    res = adapter.generate_reply({}, [], {}, rc)
    assert "Fato crucial" in res


def test_dummy_adapter_partial_admission_knowledge():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.partial_admission, allowed_knowledge=["Algo importante"])
    res = adapter.generate_reply({}, [], {}, rc)
    assert "Algo importante" in res
    # New first-person phrasing
    assert "razão" in res.lower() or "verdade" in res.lower() or "honesto" in res.lower()


def test_dummy_adapter_partial_admission_revealed_now():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.partial_admission)
    # When partial_admission with revealed_now and text is present → evidence branch runs
    # without revealed_now and without evidence_id → falls to mode branch
    revealed_now = [{"content": "O corpo foi movido"}]
    res = adapter.generate_reply({}, [], {}, rc, revealed_now=revealed_now)
    # partial_admission mode without evidence_id goes to mode branch; content must appear
    assert "honesto" in res.lower() or "história" in res.lower()


def test_dummy_adapter_neutral_answer():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.neutral_answer, allowed_facts=["O relógio parou"])
    res = adapter.generate_reply({}, [], {}, rc)
    assert "O relógio parou" in res


def test_dummy_adapter_final_phrase():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.final_phrase)
    st = {"final_phrase": "Vá embora."}
    res = adapter.generate_reply(st, [], {}, rc)
    assert res == "Vá embora."


def test_dummy_adapter_first_person():
    """NPC must not prefix response with the suspect name in third person."""
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.evasive)
    suspect_state = {"name": "Marina Souza", "personality": "nervoso"}
    res = adapter.generate_reply(suspect_state, [], {}, rc)
    assert "Marina Souza" not in res, "Response must be first-person, not narrated"


def test_dummy_adapter_evidence_without_text_blocks_reveal():
    """Presenting evidence with empty text should NOT reveal the secret."""
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.deny)
    revealed_now = [{"content": "Segredo muito importante"}]
    player_msg = {"evidence_id": 1, "text": ""}  # empty text
    res = adapter.generate_reply({}, [], player_msg, rc, revealed_now=revealed_now)
    assert "Segredo muito importante" not in res
    assert "quer dizer" in res.lower() or "fale direto" in res.lower()


def test_dummy_adapter_evidence_with_text_shows_pressure():
    """Presenting evidence with context text should show pressure reaction."""
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.deny)
    revealed_now = [{"content": "Segredo revelado"}]
    player_msg = {"evidence_id": 1, "text": "Explique essa evidência"}
    res = adapter.generate_reply({}, [], player_msg, rc, revealed_now=revealed_now)
    # Should react with pressure, not expose the secret text directly
    assert "pegou" in res.lower() or "espera" in res.lower()
    assert "Segredo revelado" not in res
