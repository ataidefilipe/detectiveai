from typing import Optional, List
from sqlalchemy.orm import Session
from app.api.schemas.chat import ConversationMemory
from app.infra.db_models import EvidenceModel

def evaluate_evidence_context(
    evidence_id: int,
    conversation_memory: ConversationMemory,
    detected_topics: Optional[List[str]] = None,
    referenced_evidence_ids: Optional[List[int]] = None,
    target_claim_ids: Optional[List[str]] = None,
    db: Session = None
) -> bool:
    """
    Avalia se a evidência apresentada pelo jogador é válida no momento atual,
    baseado na memória de curto prazo da conversa e na semântica da frase.
    
    A evidência é válida se:
      1. Não possui `related_topic_id` (é livre)
      2. `related_topic_id` está nos `detected_topics` do turno atual
      3. `related_topic_id` está em `recent_topic_ids` da memória
      4. `evidence_id` está em `referenced_evidence_ids` (GPT detectou menção)
      5. A evidência pode quebrar uma claim alvo (via evidence_code)
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

    # Regra 4: GPT referenciou esta evidência
    if referenced_evidence_ids and evidence_id in referenced_evidence_ids:
        return True

    # Regra 5: evidência pode quebrar claim alvo
    if target_claim_ids and evidence.evidence_code:
        # Buscar suspeito da evidência (via secrets)
        from app.infra.db_models import SuspectModel, SecretModel
        secret = db.query(SecretModel).filter(
            SecretModel.evidence_id == evidence_id
        ).first()
        if secret:
            suspect = db.query(SuspectModel).filter(
                SuspectModel.id == secret.suspect_id
            ).first()
            if suspect and suspect.claims:
                for claim in suspect.claims:
                    if claim.get("claim_id") in target_claim_ids:
                        breakable_ids = claim.get("breakable_by_evidence_codes", claim.get("breakable_by_evidence_ids", []))
                        if evidence.evidence_code in breakable_ids:
                            return True

    return False
