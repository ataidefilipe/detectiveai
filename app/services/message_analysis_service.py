import re
from typing import List

from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    SensitivityLevel,
    NoveltyLevel,
    SpecificityLevel
)

class MessageAnalysisService:
    """
    Serviço heurístico inicial (MVP) para analisar a mensagem do jogador
    e extrair intenção, novidade, especificidade e tópicos básicos
    antes que a arquitetura seja conectada a uma IA assistiva real.
    """

    def __init__(self):
        # Heurísticas básicas para classificar a intenção (MVP)
        self.intent_patterns = {
            MessageIntent.calm: re.compile(r'\b(calma|fique tranquilo|desculpe|relaxa|não se preocupe|tudo bem)\b', re.IGNORECASE),
            MessageIntent.pressure: re.compile(r'\b(fala logo|você está mentindo|confessa|não esconda|eu sei|pare de mentir|diga a verdade)\b', re.IGNORECASE),
            MessageIntent.ask: re.compile(r'\b(onde|quem|quando|por que|porque|como|o que|qual)\b', re.IGNORECASE)
        }
    
    def analyze_message(self, text: str) -> MessageAnalysisResult:
        """
        Analisa a mensagem de texto do jogador e retorna a classificação estruturada.
        """
        text_lower = text.lower().strip()
        
        # 1. Classificação de Intenção (Heurística simples)
        detected_intent = MessageIntent.unknown
        confidence = 0.3 # Confiança base p/ heurística desconhecida

        # Checar intenções na ordem de "peso/prioridade"
        if self.intent_patterns[MessageIntent.pressure].search(text_lower):
            detected_intent = MessageIntent.pressure
            confidence = 0.8
        elif self.intent_patterns[MessageIntent.calm].search(text_lower):
            detected_intent = MessageIntent.calm
            confidence = 0.8
        elif "?" in text or self.intent_patterns[MessageIntent.ask].search(text_lower):
            detected_intent = MessageIntent.ask
            confidence = 0.9
            
        # 2. Especificidade (baseada no tamanho da frase/palavras raras - mock MVP)
        word_count = len(text_lower.split())
        if word_count > 10:
            specificity = SpecificityLevel.high
        elif word_count > 3:
            specificity = SpecificityLevel.medium
        else:
            specificity = SpecificityLevel.low
            
        # 3. Novelty e Sensitivity virão por padrão seguros no MVP
        # O histórico real precisa vir pelo modelo em tarefas futuras (Tarefa C3/B2)
        novelty = NoveltyLevel.new 
        sensitivity_hit = SensitivityLevel.none

        return MessageAnalysisResult(
            intent=detected_intent,
            specificity=specificity,
            novelty=novelty,
            sensitivity_hit=sensitivity_hit,
            confidence=confidence,
            notes="Heuristic analysis MVP"
        )

# Instância padrão do serviço para uso nos turnos da API 
default_message_analyzer = MessageAnalysisService()

def analyze_message(text: str) -> MessageAnalysisResult:
    """Wrapper prático para o serviço de análise padrão."""
    return default_message_analyzer.analyze_message(text)
