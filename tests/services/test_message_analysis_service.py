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
