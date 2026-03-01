from app.services.ai_adapter_dummy import DummyNpcAIAdapter

ai = DummyNpcAIAdapter()

suspect_state = {
    "name": "Marina",
    "personality": "nervoso",
    "is_closed": False,
    "revealed_secrets": [],
    "hidden_secrets": [{"secret_id": 1, "content": "Algo oculto"}],
    "final_phrase": "Já falei tudo que sabia.",
}

chat_history = []

from app.api.schemas.render_context import NpcResponseRenderContext

msg = {
    "text": "Onde você estava?",
    "evidence_id": None
}

rc = NpcResponseRenderContext()

print(ai.generate_reply(
    suspect_state=suspect_state,
    chat_history=chat_history,
    player_message=msg,
    render_context=rc
))
