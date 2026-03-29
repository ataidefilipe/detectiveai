from typing import Optional, List
from sqlalchemy.orm import Session
from app.api.schemas.chat import ConversationMemory
from app.infra.db_models import EvidenceModel

def evaluate_evidence_context(
    evidence_id: int,
    conversation_memory: ConversationMemory,
    detected_topics: Optional[List[str]] = None,
    db: Session = None
) -> bool:
    """
    Avalia se a evidência apresentada pelo jogador é válida no momento atual,
    baseado na memória de curto prazo da conversa.
    
    A evidência é válida se:
      1. Não possui `related_topic_id` (é livre, serve pra qualquer hora)
      2. O `related_topic_id` está presente nos `detected_topics` do turno atual
      3. O `related_topic_id` está na janela recente de tópicos do interrogatório (`recent_topic_ids`)
      
    Args:
        evidence_id: ID numérico da evidência no DB.
        conversation_memory: Objeto ConversationMemory do turno.
        detected_topics: Lista de topic IDs detectados na mensagem atual (opcional).
        db: Sessão SQLAlchemy ativa.
        
    Returns:
        True se a evidência estiver contextualizada, False caso contrário.
    """
    evidence = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
    
    # Se não precisa de contexto de tópico, é sempre válida
    if not evidence or not evidence.related_topic_id:
        return True
        
    msg_topics = detected_topics or []
    topic_needed = evidence.related_topic_id
    
    if topic_needed in msg_topics:
        return True
        
    if topic_needed in conversation_memory.recent_topic_ids:
        return True
        
    return False
