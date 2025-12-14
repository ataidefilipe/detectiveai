"""
IA Adapter Interface for NPC Dialogue Generation.

This module defines the base interface used by the game to generate NPC
responses during interrogations. Real implementations (OpenAI, local LLM,
Claude, etc.) should inherit from `NpcAIAdapter` and override `generate_reply`.

No actual AI calls are performed in this interface.
"""

from typing import List, Dict, Any


class NpcAIAdapter:
    """
    Base interface for NPC dialogue generation.

    Any concrete implementation must override `generate_reply` and return
    a string representing the NPC's answer.

    Parameters expected:

    - suspect_state: dict with fields like:
        {
            "suspect_id": 1,
            "name": "Marina",
            "is_closed": False,
            "revealed_secrets": [
                {"secret_id": 1, "content": "...", "is_core": True},
            ],
            "personality": "cold and calculating",
            "final_phrase": "Já falei tudo que sabia."
        }

    - chat_history: list of messages (ordered), each being:
        {
            "sender": "player" | "npc",
            "text": "...",
            "evidence_id": 3 | None,
            "timestamp": "..."
        }

    - player_message: the last message sent by the player:
        {
            "text": "Explique isso",
            "evidence_id": 3 | None
        }

    Returns:
        str: the textual reply of the NPC.
    """

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        npc_context: Dict[str, Any] | None = None
    ) -> str:
        """
        npc_context:
            Contexto completo do NPC e do caso, preparado pelo backend.
            Pode conter cenário, verdades, mentiras, segredos revelados e regras.
        """

