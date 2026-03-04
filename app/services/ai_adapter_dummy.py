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

from typing import Dict, Any, List, Optional
from app.services.ai_adapter import NpcAIAdapter
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode


class DummyNpcAIAdapter(NpcAIAdapter):
    """Deterministic, rule-based NPC reply generator."""

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        render_context: NpcResponseRenderContext,
        npc_context: Dict[str, Any] | None = None,
        revealed_now: Optional[List[Dict[str, Any]]] = None
    ) -> str:

        name = suspect_state.get("name", "O suspeito")
        personality = suspect_state.get("personality", "neutro")
        is_closed = suspect_state.get("is_closed", False)
        final_phrase = suspect_state.get("final_phrase", "Já falei tudo que sabia.")
        hidden_secrets = suspect_state.get("hidden_secrets", [])
        evidence_id = player_message.get("evidence_id")

        # ----------------------------------------------------------------------
        # 1. Se o suspeito está "fechado", só devolve a frase final.
        #    Ou se o response_mode ditou final_phrase.
        # ----------------------------------------------------------------------
        if is_closed or render_context.response_mode == ResponseMode.final_phrase:
            return final_phrase

        # ----------------------------------------------------------------------
        # 2. Se o jogador usou uma evidência, reagimos a isso.
        # ----------------------------------------------------------------------
        if evidence_id is not None:
            # Se essa evidência revelou algum segredo recém descoberto...
            if revealed_now:
                revealed_texts = [s["content"] for s in revealed_now]
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
        # 3. Response mode handling (Mock deterministic responses)
        # ----------------------------------------------------------------------
        mode = render_context.response_mode
        
        # Helper to extract a single piece of allowed content
        def get_allowed_content():
            if render_context.new_knowledge_this_turn:
                return f"[Novo Conhecimento: {render_context.new_knowledge_this_turn[0]}]"
            if render_context.allowed_knowledge:
                return f"[Conhecimento Base: {render_context.allowed_knowledge[0]}]"
            if render_context.allowed_facts:
                return f"[Fato: {render_context.allowed_facts[0]}]"
            return ""

        allowed_txt = get_allowed_content()

        if mode == ResponseMode.deny:
            return f"{name} balança a cabeça negativamente. “Eu não sei nada sobre isso. É mentira.”"
            
        elif mode == ResponseMode.evasive:
            return f"{name} desvia o olhar. “Não tenho certeza... Eu não lembro direito.”"
            
        elif mode == ResponseMode.clarify:
            if allowed_txt:
                return f"{name} suspira. “Vou ser claro com você. {allowed_txt}”"
            return f"{name} tenta explicar. “Veja bem, a verdade é que as coisas são complicadas.”"
            
        elif mode == ResponseMode.partial_admission:
            if revealed_now:
                return f"{name} cede um pouco. “Ok, você me pegou nisso. {[s['content'] for s in revealed_now][0]}”"
            if allowed_txt:
                return f"{name} concorda parcialmente. “Sim, isso é parte da verdade. {allowed_txt}”"
            return f"{name} abaixa a cabeça. “Ok, você tem um ponto, mas não é toda a história...”"
            
        elif mode == ResponseMode.neutral_answer:
            if allowed_txt:
                return f"{name} responde de forma contida: “Posso confirmar que {allowed_txt}”"

        # ----------------------------------------------------------------------
        # 4. Personality Fallback (if no explicit mode match)
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

        # Personalidade neutra / fallback genérico
        return (
            f"{name} responde calmamente: "
            "“Olha, estou cooperando. Mas você precisa ser mais específico.”"
        )
