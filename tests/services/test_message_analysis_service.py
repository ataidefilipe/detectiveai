import pytest
from app.api.schemas.chat import (
    MessageIntent,
    SpecificityLevel,
    SensitivityLevel,
    NoveltyLevel
)
from app.services.message_analysis_service import analyze_message

def test_analyze_message_ask_intent():
    result = analyze_message("onde você estava ontem à noite?")
    assert result.intent == MessageIntent.ask
    assert result.confidence >= 0.8
    assert result.specificity == SpecificityLevel.medium

def test_analyze_message_pressure_intent():
    result = analyze_message("você está mentindo, confessa logo!")
    assert result.intent == MessageIntent.pressure
    assert result.confidence >= 0.8

def test_analyze_message_calm_intent():
    result = analyze_message("calma, fique tranquilo, só queremos conversar.")
    assert result.intent == MessageIntent.calm
    assert result.confidence >= 0.8

def test_analyze_message_unknown_intent():
    result = analyze_message("eu sou um detetive de polícia.")
    assert result.intent == MessageIntent.unknown
    assert result.confidence < 0.5

def test_analyze_message_specificity():
    # Long text
    resultado_alto = analyze_message("isso é um teste muito longo para verificar se a especificidade da mensagem passa a ser alta quando existem muitas palavras de forma deliberada")
    assert resultado_alto.specificity == SpecificityLevel.high
    
    # Medium text
    resultado_medio = analyze_message("o que você fez ontem?")
    assert resultado_medio.specificity == SpecificityLevel.medium
    
    # Short text
    resultado_baixo = analyze_message("entendo perfeitamente")
    assert resultado_baixo.specificity == SpecificityLevel.low

def test_analyze_message_defaults():
    # Valida defaults importantes para a fase de MVP e integrações
    result = analyze_message("ok")
    assert result.novelty == NoveltyLevel.new
    assert result.sensitivity_hit == SensitivityLevel.none
    assert result.primary_topic_id is None
    assert len(result.detected_topic_ids) == 0

def test_analyze_message_topic_detection():
    available_topics = [
        {"id": "knife", "aliases": ["faca", "adaga", "lâmina"], "is_sensitive": True},
        {"id": "wife", "aliases": ["esposa", "mulher"], "is_sensitive": False}
    ]
    
    # Test sensitive topic
    res_sens = analyze_message("eu sei que você usou a faca nela", available_topics=available_topics)
    assert res_sens.primary_topic_id == "knife"
    assert res_sens.sensitivity_hit == SensitivityLevel.high
    assert "knife" in res_sens.detected_topic_ids
    assert "knife" in res_sens.sensitive_topic_ids

    # Test normal topic
    res_norm = analyze_message("sua mulher estava lá?", available_topics=available_topics)
    assert res_norm.primary_topic_id == "wife"
    assert res_norm.sensitivity_hit == SensitivityLevel.none
    assert "wife" in res_norm.detected_topic_ids
    assert len(res_norm.sensitive_topic_ids) == 0

    # Test both
    res_both = analyze_message("a faca era da sua esposa?", available_topics=available_topics)
    assert "knife" in res_both.detected_topic_ids
    assert "wife" in res_both.detected_topic_ids
    assert res_both.sensitivity_hit == SensitivityLevel.high
    assert "knife" in res_both.sensitive_topic_ids
    assert "wife" not in res_both.sensitive_topic_ids

def test_analyze_message_novelty_repeat():
    history = [
        "onde você estava",
        "quem é você"
    ]
    # Exact match after normalization
    res1 = analyze_message("Quem é você?!", player_history=history)
    assert res1.novelty == NoveltyLevel.repeat

    # High Jaccard similarity
    history2 = ["como você explica a faca"]
    res2 = analyze_message("como você explica a faca suja", player_history=history2)
    assert res2.novelty == NoveltyLevel.repeat

def test_analyze_message_novelty_reframe():
    history = ["onde estava"]
    # Reframe: current message includes past message but is more specific
    res = analyze_message("onde estava na noite do crime", player_history=history)
    assert res.novelty == NoveltyLevel.reframe

def test_analyze_message_novelty_new():
    history = ["onde estava"]
    # New message
    res = analyze_message("qual a sua relação com a vítima?", player_history=history)
    assert res.novelty == NoveltyLevel.new


# ── T1.3: is_reframe ──────────────────────────────────────────────────────────

def test_is_reframe_false_by_default():
    """Mensagem normal não ativa is_reframe."""
    result = analyze_message("onde você estava ontem?")
    assert result.is_reframe is False


def test_is_reframe_detected_with_explicit_pattern():
    """Padrões explícitos de reformulação ativam is_reframe."""
    result = analyze_message("deixa eu perguntar de outro jeito: onde você estava?")
    assert result.is_reframe is True


def test_is_reframe_sets_novelty_reframe():
    """Quando is_reframe é detectado, novelty deve ser reframe (se não for repeat)."""
    result = analyze_message("deixa eu perguntar de outro jeito: onde você estava?")
    assert result.novelty == NoveltyLevel.reframe


def test_is_reframe_does_not_override_repeat():
    """Repetição exata NÃO é sobrescrita por reframe explícito."""
    # Mesmo que o texto contenha padrão de reframe, se for repeat pelo histórico,
    # novelty deve permanecer repeat.
    history = ["o que eu quis dizer foi: você estava em casa?"]
    result = analyze_message("o que eu quis dizer foi: você estava em casa?", player_history=history)
    assert result.novelty == NoveltyLevel.repeat


def test_is_reframe_pattern_o_que_quis_dizer():
    result = analyze_message("O que eu quis dizer é que o horário não bate.")
    assert result.is_reframe is True


def test_is_reframe_pattern_reformular():
    result = analyze_message("Vou reformular: onde você realmente estava?")
    assert result.is_reframe is True


# ── T1.3: is_meta_behavior_read ───────────────────────────────────────────────

def test_is_meta_behavior_false_by_default():
    """Mensagem normal não ativa is_meta_behavior_read."""
    result = analyze_message("onde você estava?")
    assert result.is_meta_behavior_read is False


def test_is_meta_behavior_hesitou():
    result = analyze_message("você hesitou antes de responder.")
    assert result.is_meta_behavior_read is True


def test_is_meta_behavior_antes_voce_disse():
    result = analyze_message("antes você disse que estava em casa, mas agora muda a história?")
    assert result.is_meta_behavior_read is True


def test_is_meta_behavior_sua_reacao():
    result = analyze_message("sua reação ao ver a foto foi muito suspeita.")
    assert result.is_meta_behavior_read is True


def test_is_meta_behavior_notei_que_voce():
    result = analyze_message("notei que você desviou o olhar quando perguntei sobre a faca.")
    assert result.is_meta_behavior_read is True


# ── T1.3: inferred_claim_targets defaults ─────────────────────────────────────

def test_inferred_claim_targets_defaults_empty():
    """inferred_claim_targets começa vazio (será preenchido no Sprint 2)."""
    result = analyze_message("onde você estava?")
    assert result.inferred_claim_targets == []
