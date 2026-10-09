from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult
from app.api.schemas.render_context import NpcResponseRenderContext, ResponseMode, NarrativeMemoryView
from typing import Optional, List
from app.infra.db_models import SuspectModel

MAX_MUST_SAY_PER_TURN: int = 2

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
    narrative_memory: Optional[NarrativeMemoryView] = None,
    pressure: float = 0.0,
    patience: float = 50.0
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

    from app.services.npc_mode_policy_service import determine_response_mode, determine_speech_directive
    from app.domain.schema_scenario import SpeechProfile

    response_mode = determine_response_mode(
        transition=transition,
        analysis=analysis,
        has_newly_broken_claims=bool(newly_broken_claims),
        has_revealed_secrets=bool(revealed_facts),
        has_new_knowledge=bool(new_knowledge_this_turn),
        evidence_effect=evidence_effect
    )
    
    npc_stance = current_stance or (transition.npc_shift.value if transition.npc_shift != NpcShift.none else "neutral")

    # Modulação de fala e verbosidade (Sprint 3 / Astra UX)
    speech_profile = None
    if suspect is not None:
        prof = getattr(suspect, "profile", None)
        if prof is None and isinstance(suspect, dict):
            prof = suspect.get("profile")
        if prof is not None:
            if isinstance(prof, dict):
                speech_data = prof.get("speech")
                if speech_data and isinstance(speech_data, dict):
                    speech_profile = SpeechProfile(**speech_data)
                elif "base_verbosity" in prof:
                    speech_profile = SpeechProfile(**prof)
            elif hasattr(prof, "speech"):
                speech_profile = getattr(prof, "speech", None)

    speech_directive = determine_speech_directive(
        profile=speech_profile,
        pressure=pressure,
        patience=patience,
        stance=npc_stance,
        response_mode=response_mode,
    )
    
    # ── Sprint 3 T5.1 & Parecer Astra: Categorizar e desduplicar conteúdo ──
    must_say = []
    may_say = []
    
    # 1. Segredo recém-revelado → prioridade em must_say (desduplicado)
    if allowed_facts:
        for f in allowed_facts:
            if f and f not in must_say:
                must_say.append(f)

    # 2. Conhecimento novo neste turno:
    # Se houver segredo em must_say e a nova camada de conhecimento tiver alta sobreposição
    # léxica com ele, colocamos no may_say para evitar dumping monolítico forçado.
    if new_knowledge_this_turn:
        for k in new_knowledge_this_turn:
            if not k or k in must_say:
                continue
            
            is_redundant_with_secret = False
            if allowed_facts:
                k_words = set(w.lower() for w in k.split() if len(w) > 4)
                for f in allowed_facts:
                    f_words = set(w.lower() for w in f.split() if len(w) > 4)
                    if k_words and len(k_words.intersection(f_words)) / len(k_words) >= 0.5:
                        is_redundant_with_secret = True
                        break
            
            if is_redundant_with_secret:
                if k not in may_say:
                    may_say.append(k)
            else:
                must_say.append(k)

    # 3. Conhecimento antigo permitido → may_say (se não estiver em must_say)
    if allowed_knowledge:
        for k in allowed_knowledge:
            if k and k not in must_say and k not in may_say:
                may_say.append(k)

    # 4. Teto de must_say por turno para evitar monólogos descarregando múltiplos fatos de uma só vez
    if len(must_say) > MAX_MUST_SAY_PER_TURN:
        overflow = must_say[MAX_MUST_SAY_PER_TURN:]
        must_say = must_say[:MAX_MUST_SAY_PER_TURN]
        for item in reversed(overflow):
            if item not in may_say:
                may_say.insert(0, item)

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
        narrative_memory=narrative_memory or NarrativeMemoryView(),
        speech_directive=speech_directive
    )
