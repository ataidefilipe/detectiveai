from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode

def test_dummy_adapter_deny():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.deny)
    res = adapter.generate_reply({}, [], {}, rc)
    assert "não sei nada sobre isso" in res.lower()
    assert "mentira" in res.lower()

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
    assert "concorda parcialmente" in res.lower()

def test_dummy_adapter_partial_admission_revealed_now():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.partial_admission)
    revealed_now = [{"content": "O corpo foi movido"}]
    res = adapter.generate_reply({}, [], {}, rc, revealed_now=revealed_now)
    assert "O corpo foi movido" in res
    assert "cede um pouco" in res.lower()

def test_dummy_adapter_neutral_answer():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.neutral_answer, allowed_facts=["O relógio parou"])
    res = adapter.generate_reply({}, [], {}, rc)
    assert "O relógio parou" in res

def test_dummy_adapter_final_phrase():
    adapter = DummyNpcAIAdapter()
    rc = NpcResponseRenderContext(response_mode=ResponseMode.final_phrase)
    state = {"final_phrase": "Vá embora."}
    res = adapter.generate_reply(state, [], {}, rc)
    assert res == "Vá embora."
