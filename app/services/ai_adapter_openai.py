import os
from typing import Dict, Any, List

from openai import OpenAI
from app.services.ai_adapter import NpcAIAdapter
from app.services.prompt_builder import build_npc_prompt


class OpenAINpcAIAdapter(NpcAIAdapter):
    """
    Real AI adapter using OpenAI Responses API.

    IMPORTANT:
    - This adapter receives ONLY already-allowed information
    - It must never infer or invent secrets
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    def generate_reply(
        self,
        suspect_state: dict,
        chat_history: list,
        player_message: dict,
        npc_context: dict | None = None
    ) -> str:
        if not npc_context:
            raise ValueError("npc_context is required for OpenAI adapter")

        prompt = build_npc_prompt(
            npc_context=npc_context,
            chat_history=chat_history,
            player_message=player_message
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text.strip()
