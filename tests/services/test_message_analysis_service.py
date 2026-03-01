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

    # Test normal topic
    res_norm = analyze_message("sua mulher estava lá?", available_topics=available_topics)
    assert res_norm.primary_topic_id == "wife"
    assert res_norm.sensitivity_hit == SensitivityLevel.none
    assert "wife" in res_norm.detected_topic_ids

    # Test both
    res_both = analyze_message("a faca era da sua esposa?", available_topics=available_topics)
    assert "knife" in res_both.detected_topic_ids
    assert "wife" in res_both.detected_topic_ids
    assert res_both.sensitivity_hit == SensitivityLevel.high
