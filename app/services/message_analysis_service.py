import os
import logging
from typing import List, Optional

from app.api.schemas.chat import MessageAnalysisResult
from app.services.message_classifier import MessageClassifier, HeuristicMessageClassifier

logger = logging.getLogger(__name__)


def _create_classifier() -> MessageClassifier:
    """
    T1.2 — Creates the appropriate classifier based on MESSAGE_CLASSIFIER_PROVIDER env.
    Supports: 'heuristic' (default) | 'openai'.
    Falls back to heuristic if OpenAI initialization fails.
    """
    provider = os.getenv("MESSAGE_CLASSIFIER_PROVIDER", "heuristic").lower()

    if provider == "openai":
        try:
            from app.services.message_classifier_openai import OpenAISemanticMessageClassifier
            logger.info("[classifier] Using OpenAI semantic classifier")
            return OpenAISemanticMessageClassifier()
        except Exception as e:
            logger.warning(f"[classifier] Failed to init OpenAI classifier: {e}. Falling back to heuristic.")
            return HeuristicMessageClassifier()

    logger.info("[classifier] Using heuristic classifier")
    return HeuristicMessageClassifier()


class MessageAnalysisService:
    """
    Gerenciador/Wrapper de Análise de Mensagem.
    Neste estágio (MVP), ele mantém por padrão a instância do classificador heurístico,
    mas a arquitetura já está preparada para que a instância do `classifier` 
    seja trocada ou injetada futuramente por um classificador baseado em ML/LLM.
    """
    def __init__(self, classifier: Optional[MessageClassifier] = None):
        if classifier is None:
            self.classifier = _create_classifier()
        else:
            self.classifier = classifier

    def analyze_message(self, text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None, **kwargs) -> MessageAnalysisResult:
        """
        Delega a análise da mensagem de texto do jogador e cruzamento de tópicos
        para o classificador embutido (heurístico no MVP).
        """
        return self.classifier.classify(text, available_topics=available_topics, player_history=player_history, **kwargs)


# Instância padrão do serviço para uso nos turnos da API 
default_message_analyzer = MessageAnalysisService()

def analyze_message(text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None, **kwargs) -> MessageAnalysisResult:
    """Wrapper prático para o serviço de análise padrão."""
    return default_message_analyzer.analyze_message(text, available_topics, player_history, **kwargs)

