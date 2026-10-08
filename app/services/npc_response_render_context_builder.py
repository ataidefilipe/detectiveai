from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode, NarrativeMemoryView
from typing import Optional, List
from app.infra.db_models import SuspectModel

def build_render_context(
    transition: StateTransitionResult,
    analysis: MessageAnalysisResult,
    revealed_facts: Optional[List[str]] = None,
    allowed_knowledge: Optional[List[str]] = None,
    new_knowledge_this_turn: Optional[List[str]] = None,
    suspect: Optional[SuspectModel] = None,
    evidence_effect: str = "none",
    newly_broken_claims: Optional[List[dict]] = None,
    current_stance: Optional[str] = None,
    narrative_memory: Optional[NarrativeMemoryView] = None
) -> NpcResponseRenderContext:
    """
    Constrói o NpcResponseRenderContext, decidindo a diretriz de atuação da LLM
    com as decisões já tomadas pelo motor mecânico do jogo.

    IMPORTANTE: 'allowed_knowledge' serve apenas como insumo de decisão para o 'response_mode' 
    dentro deste builder. O prompt final (prompt_builder.py) utiliza 'npc_context["revealed_knowledge"]' 
    (persistido no banco) como fonte de memória. Não trate os dois como sinônimos.
    """

    # Map back dicts to strings if necessary. revealed_facts can be list of dicts from SecretModel
    if revealed_facts:
        allowed_facts = [f["content"] if isinstance(f, dict) else f for f in revealed_facts]
    else:
        allowed_facts = []

    from app.services.npc_mode_policy_service import determine_response_mode
    response_mode = determine_response_mode(
        transition=transition,
        analysis=analysis,
        has_newly_broken_claims=bool(newly_broken_claims),
        has_revealed_secrets=bool(revealed_facts),
        has_new_knowledge=bool(new_knowledge_this_turn),
        evidence_effect=evidence_effect
    )
    
    npc_stance = current_stance or (transition.npc_shift.value if transition.npc_shift != NpcShift.none else "neutral")
    
    # ── Sprint 3 T5.1: Categorizar conteúdo ──────────────────────────────────
    must_say = []
    may_say = []
    
    # Segredo recém-revelado → must_say
    if allowed_facts:
        must_say.extend(allowed_facts)

    # Conhecimento novo neste turno → must_say
    if new_knowledge_this_turn:
        must_say.extend(new_knowledge_this_turn)

    # Conhecimento antigo → may_say
    if allowed_knowledge:
        may_say.extend([k for k in allowed_knowledge if k not in must_say])

    must_not_say = ["alibi_contradiction"] if transition.npc_shift == NpcShift.more_defensive else []

    # Map claim_id to statement if available
    pressure_texts = []
    if newly_broken_claims and suspect and suspect.claims:
        claim_map = {c["claim_id"]: c.get("statement") or c.get("text") for c in suspect.claims}
        pressure_texts = [claim_map[c["claim_id"]] for c in newly_broken_claims if c["claim_id"] in claim_map]
    
    return NpcResponseRenderContext(
        response_mode=response_mode,
        npc_stance=npc_stance,
        allowed_facts=allowed_facts,
        allowed_knowledge=allowed_knowledge or [],
        new_knowledge_this_turn=new_knowledge_this_turn or [],
        player_intent=analysis.intent.value,
        tone_hint=None, # Definido para testes no MVP
        forbidden_topics=must_not_say,
        active_topic_id=analysis.primary_topic_id,
        claim_pressure_summary=pressure_texts,
        must_say=must_say,
        may_say=may_say,
        must_not_say=must_not_say,
        narrative_memory=narrative_memory or NarrativeMemoryView()
    )
