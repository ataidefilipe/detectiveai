"""
Dummy implementation of NpcAIAdapter.

This adapter does NOT use any real AI model.
It produces deterministic responses based on:
- revealed secrets
- hidden secrets
- personality
- evidence usage
- whether the suspect is 'closed'

Useful for testing the entire interrogation flow before integrating a real LLM.
"""

from typing import Dict, Any, List
from app.services.ai_adapter import NpcAIAdapter


class DummyNpcAIAdapter(NpcAIAdapter):
    """Deterministic, rule-based NPC reply generator."""

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        npc_context: Dict[str, Any] | None = None
    ) -> str:

        name = suspect_state.get("name", "O suspeito")
        personality = suspect_state.get("personality", "neutro")
        is_closed = suspect_state.get("is_closed", False)
        final_phrase = suspect_state.get("final_phrase", "Já falei tudo que sabia.")
        revealed_secrets = suspect_state.get("revealed_secrets", [])
        hidden_secrets = suspect_state.get("hidden_secrets", [])
        evidence_id = player_message.get("evidence_id")

        # ----------------------------------------------------------------------
        # 1. Se o suspeito está "fechado", só devolve a frase final.
        # ----------------------------------------------------------------------
        if is_closed:
            return final_phrase

        # ----------------------------------------------------------------------
        # 2. Se o jogador usou uma evidência, reagimos a isso.
        # ----------------------------------------------------------------------
        if evidence_id is not None:
            # Se essa evidência revelou algum segredo recém descoberto...
            if revealed_secrets:
                revealed_texts = [s["content"] for s in revealed_secrets]
                combined = " ".join(revealed_texts)
                return (
                    f"...Tá bom, tá bom! Essa evidência me incrimina. "
                    f"{combined}"
                )
            else:
                return (
                    f"Isso? {name} olha para a evidência e dá de ombros. "
                    "“Isso não prova nada. Você está exagerando.”"
                )

        # ----------------------------------------------------------------------
        # 3. Se a pergunta não tem evidência, retornar algo genérico.
        # ----------------------------------------------------------------------

        if personality == "agressivo":
            return (
                f"{name} cruza os braços. “Por que eu perderia meu tempo respondendo isso? "
                "Fale algo que faça sentido.”"
            )
        elif personality == "nervoso":
            return (
                f"{name} engole seco. “E-eu já disse tudo o que sei. "
                "Vocês estão me assustando.”"
            )
        elif personality == "arrogante":
            return (
                f"{name} sorri com desprezo. “Vocês detetives são todos iguais. "
                "Perguntam demais e entendem de menos.”"
            )

        # Personalidade neutra / fallback
        return (
            f"{name} responde calmamente: "
            "“Olha, estou cooperando. Mas você precisa ser mais específico.”"
        )
