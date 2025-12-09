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

msg = {
    "text": "Onde você estava?",
    "evidence_id": None
}

print(ai.generate_reply(suspect_state, chat_history, msg))
