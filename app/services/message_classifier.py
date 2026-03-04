import re
from abc import ABC, abstractmethod
from typing import List, Optional

from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    SensitivityLevel,
    NoveltyLevel,
    SpecificityLevel
)

class MessageClassifier(ABC):
    """
    Interface base para classificadores de mensagens do jogador.
    Abstrai a lógica (heurística vs LLM) do resto do sistema.
    """
    
    @abstractmethod
    def classify(self, text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None, **kwargs) -> MessageAnalysisResult:
        """
        Recebe o texto do jogador e tópicos para extrair a intenção e os hits.
        O player_history opcional é uma lista das ultimas mensagens para calculo de novelty.
        """
        pass


class HeuristicMessageClassifier(MessageClassifier):
    """
    Implementação Heurística (MVP) baseada em Expressões Regulares e
    contadores estáticos para classificar intenção, novidade e extrair tópicos.
    """

    def __init__(self):
        # Heurísticas básicas para classificar a intenção
        self.intent_patterns = {
            MessageIntent.calm: re.compile(r'\b(calma|fique tranquilo|desculpe|relaxa|não se preocupe|tudo bem)\b', re.IGNORECASE),
            MessageIntent.pressure: re.compile(r'\b(fala logo|você está mentindo|confessa|não esconda|eu sei|pare de mentir|diga a verdade)\b', re.IGNORECASE),
            MessageIntent.ask: re.compile(r'\b(onde|quem|quando|por que|porque|como|o que|qual)\b', re.IGNORECASE)
        }

    def classify(self, text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None, **kwargs) -> MessageAnalysisResult:
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
            
        # 3. Extração de Tópicos
        detected_topic_ids = []
        sensitive_topic_ids = []
        primary_topic_id = None
        sensitivity_hit = SensitivityLevel.none

        if available_topics:
            for topic in available_topics:
                aliases = topic.get("aliases", [])
                
                # Create a simple \b word \b matcher for all aliases
                if aliases:
                    # Escape aliases to be safe, join with |
                    pattern_str = r'\b(' + '|'.join(re.escape(a.strip()) for a in aliases) + r')\b'
                    matcher = re.compile(pattern_str, re.IGNORECASE)
                    
                    if matcher.search(text_lower):
                        detected_topic_ids.append(topic["id"])
                        
                        if topic.get("is_sensitive"):
                            sensitive_topic_ids.append(topic["id"])
                            sensitivity_hit = SensitivityLevel.high
                            
            if detected_topic_ids:
                # Naive primary assignment for MVP
                primary_topic_id = detected_topic_ids[0]

        # 4. Novelty análise com histórico
        novelty = NoveltyLevel.new
        if player_history:
            import string
            def normalize(s: str) -> str:
                return s.lower().translate(str.maketrans('', '', string.punctuation)).strip()
            
            norm_text = normalize(text)
            current_words = set(norm_text.split())
            
            for past_msg in player_history:
                norm_past = normalize(past_msg)
                if not norm_past:
                    continue
                    
                # Repetição exata
                if norm_text == norm_past:
                    novelty = NoveltyLevel.repeat
                    break
                
                past_words = set(norm_past.split())
                if not past_words or not current_words:
                    continue
                    
                # Jaccard similarity para repetição quase exata
                intersection = current_words.intersection(past_words)
                union = current_words.union(past_words)
                similarity = len(intersection) / len(union) if len(union) > 0 else 0
                
                if similarity > 0.8:
                    novelty = NoveltyLevel.repeat
                    break
                
                # Reframe: a mensagem atual engloba a passada, mas é mais específica
                if past_words.issubset(current_words) and len(current_words) > len(past_words):
                    if novelty != NoveltyLevel.repeat:
                        novelty = NoveltyLevel.reframe

        notes = "Heuristic analysis MVP"
        if novelty != NoveltyLevel.new:
            notes += f" | novelty={novelty.value}"

        return MessageAnalysisResult(
            primary_topic_id=primary_topic_id,
            detected_topic_ids=detected_topic_ids,
            sensitive_topic_ids=sensitive_topic_ids,
            intent=detected_intent,
            specificity=specificity,
            novelty=novelty,
            sensitivity_hit=sensitivity_hit,
            confidence=confidence,
            notes=notes
        )
