import os

from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.services.ai_adapter_openai import OpenAINpcAIAdapter


def get_npc_ai_adapter():
    provider = os.getenv("NPC_AI_PROVIDER", "dummy").lower()

    if provider == "openai":
        return OpenAINpcAIAdapter()

    # default / fallback
    return DummyNpcAIAdapter()
