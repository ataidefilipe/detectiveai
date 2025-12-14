import os

from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.services.ai_adapter_openai import OpenAINpcAIAdapter


def get_npc_ai_adapter():
    provider = os.getenv("NPC_AI_PROVIDER", "dummy").lower()
    print(f"[AI] NPC_AI_PROVIDER = {provider}")

    if provider == "openai":
        print("[AI] Using OpenAI adapter")
        return OpenAINpcAIAdapter()

    print("[AI] Using Dummy adapter")
    return DummyNpcAIAdapter()
