from app.api.schemas.chat import StateTransitionResult, NpcShift, MessageAnalysisResult, MessageIntent
from app.api.schemas.render_context import ResponseMode, SpeechDirective
from app.domain.schema_scenario import SpeechProfile
from typing import Optional, List, Dict, Any

def determine_response_mode(
    transition: StateTransitionResult,
    analysis: MessageAnalysisResult,
    has_newly_broken_claims: bool = False,
    has_revealed_secrets: bool = False,
    has_new_knowledge: bool = False,
    evidence_effect: str = "none"
) -> ResponseMode:
    """
    Decide qual será a diretriz de atuação da LLM com as decisões já tomadas pelo motor mecânico.
    Regras MVP:
    * explore + baixa pressão -> neutral_answer
    * pressure sem prova -> guarded ou evasive
    * claim quebrado -> partial_admission ou contradiction_repair
    """

    # 1. Admissões ou reparos por quebra (Sprint 3 T5.2)
    if has_newly_broken_claims:
        return ResponseMode.claim_reaction
        
    if has_revealed_secrets:
        return ResponseMode.evidence_reaction

    if has_new_knowledge:
        if transition.npc_shift == NpcShift.more_defensive:
            return ResponseMode.contradiction_repair
        return ResponseMode.partial_admission

    # 1.5. Repetição e Falta de Especificidade
    from app.api.schemas.chat import NoveltyLevel, SpecificityLevel
    if analysis.novelty == NoveltyLevel.repeat:
        return ResponseMode.irritated_repeat
        
    if analysis.specificity == SpecificityLevel.low and not analysis.detected_topic_ids:
        return ResponseMode.context_request

    # 2. Deflexão sob pressão ou efeito adverso de evidência
    if evidence_effect == "out_of_context":
        if transition.npc_shift == NpcShift.more_defensive:
            return ResponseMode.deny
        return ResponseMode.evasive
        
    if transition.npc_shift == NpcShift.pressured:
        if evidence_effect == "reaction_only":
            return ResponseMode.pressured_deflection
        return ResponseMode.guarded

    if transition.npc_shift == NpcShift.more_defensive:
        if analysis.intent == MessageIntent.pressure:
            return ResponseMode.guarded
        return ResponseMode.deny

    # 3. Interações normais
    if analysis.intent == MessageIntent.pressure:
        return ResponseMode.guarded

    if transition.npc_shift == NpcShift.more_cooperative:
        return ResponseMode.clarify

    return ResponseMode.neutral_answer


def determine_speech_directive(
    profile: Optional[SpeechProfile] = None,
    pressure: float = 0.0,
    patience: float = 50.0,
    stance: str = "neutral",
    response_mode: Optional[ResponseMode] = None,
) -> SpeechDirective:
    """
    Calcula deterministamente a diretriz de verbosidade e ritmo do suspeito
    com base no perfil de fala, estado de estresse/pressão e modo de resposta.
    """
    if profile is None:
        profile = SpeechProfile()

    p = max(0.0, min(1.0, float(pressure) / 100.0))
    impatience = max(0.0, min(1.0, 1.0 - (float(patience) / 100.0)))

    raw_verbosity = profile.base_verbosity + (profile.stress_verbosity_delta * p) - (0.15 * impatience)
    verbosity = max(0.0, min(1.0, raw_verbosity))

    if response_mode == ResponseMode.context_request:
        return SpeechDirective(
            min_sentences=1,
            max_sentences=1,
            target_max_words=25,
            rhythm_hint="pergunta curta e direta pedindo especificidade, sem reapresentação ou rodeios"
        )

    if response_mode == ResponseMode.irritated_repeat:
        return SpeechDirective(
            min_sentences=1,
            max_sentences=2,
            target_max_words=40,
            rhythm_hint="impaciente e cortante com a repetição; corte rodeios"
        )

    if verbosity < 0.30:
        min_s = 1
        max_s = 2
        words = 35
        if p > 0.6 and profile.stress_verbosity_delta < 0:
            rhythm = "fala extremamente seca, lacônica e contida sob pressão; respostas curtas, cortantes e econômicas"
        else:
            rhythm = "fala seca, contida e econômica; respostas diretas e curtas"
    elif verbosity <= 0.70:
        min_s = 2
        max_s = 3
        words = 65
        rhythm = "tom equilibrado e ponderado; respostas naturais e objetivas"
    else:
        min_s = 3
        max_s = 5
        words = 95
        if p > 0.6 and profile.stress_verbosity_delta > 0:
            rhythm = "ansiosa e detalhista sob pressão, com tentativas de se explicar, justificar ou corrigir; sem gagueira caricatural"
        else:
            rhythm = "expressiva e detalhista; respostas mais articuladas e explicativas"

    if stance == "defensive" and verbosity <= 0.70:
        rhythm += "; defensivo e evasivo, medindo as palavras"

    return SpeechDirective(
        min_sentences=min_s,
        max_sentences=max_s,
        target_max_words=words,
        rhythm_hint=rhythm
    )

