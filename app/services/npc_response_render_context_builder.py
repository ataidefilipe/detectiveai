from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode
from typing import Optional, List
from app.infra.db_models import SuspectModel

def build_render_context(
    transition: StateTransitionResult,
    analysis: MessageAnalysisResult,
    revealed_facts: Optional[List[str]] = None,
    allowed_knowledge: Optional[List[str]] = None,
    new_knowledge_this_turn: Optional[List[str]] = None,
    suspect: Optional[SuspectModel] = None,
    evidence_effect: str = "none"
) -> NpcResponseRenderContext:
    """
    Constrói o NpcResponseRenderContext, decidindo a diretriz de atuação da LLM
    com as decisões já tomadas pelo motor mecânico do jogo (MVP).
    """

    # Default
    response_mode = ResponseMode.neutral_answer
    npc_stance = transition.npc_shift.value
    
    # Map back dicts to strings if necessary. revealed_facts can be list of dicts from SecretModel
    if revealed_facts:
        allowed_facts = [f["content"] if isinstance(f, dict) else f for f in revealed_facts]
    else:
        allowed_facts = []

    # Map state transitions to strict LLM directives
    # 1. Se revealed_facts tiver itens novos -> partial_admission
    if revealed_facts:
        response_mode = ResponseMode.partial_admission
        
    # 2. Se evidence_effect == "out_of_context"
    elif evidence_effect == "out_of_context":
        if transition.npc_shift == NpcShift.more_defensive:
            response_mode = ResponseMode.deny
        else:
            response_mode = ResponseMode.evasive
            
    # 3. Se pressured E houver allowed_knowledge -> partial_admission
    elif transition.npc_shift == NpcShift.pressured:
        if allowed_knowledge or new_knowledge_this_turn:
            response_mode = ResponseMode.partial_admission
        else:
            response_mode = ResponseMode.evasive
            
    # 4. Se more_defensive SEM novos conteúdos -> deny
    elif transition.npc_shift == NpcShift.more_defensive:
        response_mode = ResponseMode.deny
        
    # 5. Fallbacks pro humor/stance normal
    elif transition.npc_shift == NpcShift.more_cooperative:
        response_mode = ResponseMode.clarify

    # No futuro (fase D), a Reveal Policy Service adicionará 'Knowledges' ao 'allowed_facts'
    
    return NpcResponseRenderContext(
        response_mode=response_mode,
        npc_stance=npc_stance,
        allowed_facts=allowed_facts,
        allowed_knowledge=allowed_knowledge or [],
        new_knowledge_this_turn=new_knowledge_this_turn or [],
        player_intent=analysis.intent.value,
        tone_hint=None, # Definido para testes no MVP
        forbidden_topics=["alibi_contradiction"] if transition.npc_shift == NpcShift.more_defensive else []
    )
