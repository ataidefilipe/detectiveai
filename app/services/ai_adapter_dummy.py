"""
Dummy implementation of NpcAIAdapter.

This adapter does NOT use any real AI model.
It produces deterministic first-person responses based on:
- revealed secrets
- render_context.response_mode
- player message text
- personality

Useful for testing the entire interrogation flow before integrating a real LLM.
"""

from typing import Dict, Any, List, Optional
from app.services.ai_adapter import NpcAIAdapter
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode


class DummyNpcAIAdapter(NpcAIAdapter):
    """Deterministic, rule-based NPC reply generator. Speaks in first person."""

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        render_context: NpcResponseRenderContext,
        npc_context: Dict[str, Any] | None = None,
        revealed_now: Optional[List[Dict[str, Any]]] = None,
        effective_message_ids: Optional[List[int]] = None  # AI-002
    ) -> str:

        personality = suspect_state.get("personality", "neutro")
        is_closed = suspect_state.get("is_closed", False)
        final_phrase = suspect_state.get("final_phrase", "Já falei tudo que sabia.")
        evidence_id = player_message.get("evidence_id")
        player_text = (player_message.get("text") or "").strip()

        # ── 1. Fechado / frase final ─────────────────────────────
        if is_closed or render_context.response_mode == ResponseMode.final_phrase:
            return final_phrase

        # ── 2. Evidência apresentada ─────────────────────────────
        if evidence_id is not None:
            # Sem contexto textual — não entrega o segredo diretamente
            if len(player_text) < 4:
                return (
                    "Isso aí? O que você quer dizer com isso? "
                    "Se tem algo a dizer, fale direto."
                )

            # Com contexto e motor revelou segredo → reage com pressão, não repete o conteúdo
            if revealed_now and len(revealed_now) > 0:
                return (
                    "Eu... espera. De onde você tirou isso? "
                    "[pausa] Tudo bem. Você me pegou. Mas não é tão simples quanto parece."
                )
            else:
                return (
                    "Isso não prova nada. Você está tirando conclusões precipitadas. "
                    "Precisa de mais do que isso pra me acusar."
                )

        # ── 3. Por modo de resposta ──────────────────────────────
        mode = render_context.response_mode

        def get_allowed_content():
            if render_context.new_knowledge_this_turn:
                return render_context.new_knowledge_this_turn[0]
            if render_context.allowed_knowledge:
                return render_context.allowed_knowledge[0]
            if render_context.allowed_facts:
                return render_context.allowed_facts[0]
            return ""

        content = get_allowed_content()

        if mode == ResponseMode.deny:
            return "Eu não sei nada sobre isso. Estão me acusando de coisas que não fiz."

        elif mode == ResponseMode.evasive:
            return "Não tenho certeza... Não lembro direito. Faz muito tempo."

        elif mode == ResponseMode.clarify:
            if content:
                return f"Vou ser direto com você. {content}"
            return "Olha, as coisas são mais complicadas do que parecem. Não é fácil explicar."

        elif mode == ResponseMode.partial_admission:
            if content:
                return f"Ok, você tem razão em parte. {content} Mas não é a história toda."
            return "Tudo bem, talvez eu não tenha sido completamente honesto. Mas tinha motivos."

        elif mode == ResponseMode.neutral_answer:
            if content:
                return f"Posso confirmar que {content}"
            return "Estou cooperando com a investigação. Pergunte o que quiser."

        # ── 4. Fallback por personalidade ────────────────────────
        if personality == "agressivo":
            return (
                "Chega de perguntas. Se tem prova de alguma coisa, mostre. "
                "Caso contrário, estou indo embora."
            )
        elif personality == "nervoso":
            return (
                "E-eu já disse tudo o que sei. Por que ficam me pressionando assim? "
                "Não fiz nada de errado!"
            )
        elif personality == "arrogante":
            return (
                "Vocês detetives são todos iguais. Perguntam muito e entendem de menos. "
                "Tente algo mais inteligente."
            )

        # Personalidade neutra / fallback genérico
        return "Olha, estou cooperando. Mas você precisa ser mais específico."
