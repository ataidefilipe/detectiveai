import os

from typing import Optional
from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.services.ai_adapter_openai import OpenAINpcAIAdapter


def get_npc_ai_adapter(api_key: Optional[str] = None, model: Optional[str] = None):
    provider = os.getenv("NPC_AI_PROVIDER", "dummy").lower()

    if api_key or provider == "openai":
        return OpenAINpcAIAdapter(api_key=api_key, model=model)

    return DummyNpcAIAdapter()
