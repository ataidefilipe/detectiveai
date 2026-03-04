from typing import List, Optional

from app.api.schemas.chat import MessageAnalysisResult
from app.services.message_classifier import MessageClassifier, HeuristicMessageClassifier

class MessageAnalysisService:
    """
    Gerenciador/Wrapper de Análise de Mensagem.
    Neste estágio (MVP), ele mantém por padrão a instância do classificador heurístico,
    mas a arquitetura já está preparada para que a instância do `classifier` 
    seja trocada ou injetada futuramente por um classificador baseado em ML/LLM.
    """
    def __init__(self, classifier: Optional[MessageClassifier] = None):
        if classifier is None:
            self.classifier = HeuristicMessageClassifier()
        else:
            self.classifier = classifier

    def analyze_message(self, text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None) -> MessageAnalysisResult:
        """
        Delega a análise da mensagem de texto do jogador e cruzamento de tópicos
        para o classificador embutido (heurístico no MVP).
        """
        return self.classifier.classify(text, available_topics=available_topics, player_history=player_history)


# Instância padrão do serviço para uso nos turnos da API 
default_message_analyzer = MessageAnalysisService()

def analyze_message(text: str, available_topics: Optional[List[dict]] = None, player_history: Optional[List[str]] = None) -> MessageAnalysisResult:
    """Wrapper prático para o serviço de análise padrão."""
    return default_message_analyzer.analyze_message(text, available_topics, player_history)
