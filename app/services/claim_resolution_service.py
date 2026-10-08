from typing import List, Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from app.infra.db_models import SessionClaimStateModel, SuspectModel, EvidenceModel
from app.api.schemas.chat import MessageAnalysisResult, ConversationMemory

def resolve_broken_claims(
    session_id: int,
    suspect_id: int,
    evidence_id: Optional[int] = None,
    analysis: Optional[MessageAnalysisResult] = None,
    conversation_memory: Optional[ConversationMemory] = None,
    db: Session = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Avalia se alguma claim do suspeito deve ser quebrada no turno atual.
    
    Returns:
        Uma tupla contendo:
        1. Lista com dicionários de claims quebradas (ClaimEvent schema).
        2. Lista de IDs (`reveal_on_break`) que devem ser destravados como recompensa.
    """
    newly_broken_claims = []
    rewards_to_reveal = []
    
    suspect = db.query(SuspectModel).filter(SuspectModel.id == suspect_id).first()
    if not suspect or not suspect.claims:
        return [], []
        
    config_claims = {c["claim_id"]: c for c in suspect.claims}
    
    claim_states = db.query(SessionClaimStateModel).filter(
        SessionClaimStateModel.session_id == session_id,
        SessionClaimStateModel.suspect_id == suspect_id,
        SessionClaimStateModel.status == "active"
    ).all()
    
    has_broken_claims = False
    
    for state in claim_states:
        claim_config = config_claims.get(state.claim_id)
        if not claim_config:
            continue
            
        broken = False
        broken_ev_id = None
        broken_cl_id = None
        
        # 1. Quebra por evidência objetiva
        breakable_codes = claim_config.get("breakable_by_evidence_codes", 
                                            claim_config.get("breakable_by_evidence_ids", []))
        if evidence_id and breakable_codes:
            evidence = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
            if evidence:
                matched = evidence.evidence_code in breakable_codes
                # Warning para match por nome (legado)
                if not matched and evidence.name in breakable_codes:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"[claim] Claim {state.claim_id} matched by evidence name '{evidence.name}' "
                        f"instead of code. Please update scenario to use evidence_code."
                    )
                    matched = True
                
                if matched:
                    # Require context match for evidence breaks
                    topic_id = claim_config.get("topic_id")
                    
                    is_context_match = True
                    if topic_id:
                        active_topics = []
                        last_topic_id = None
                        if analysis:
                            active_topics = analysis.detected_topic_ids
                        if conversation_memory:
                            last_topic_id = conversation_memory.active_topic_id
                            if not last_topic_id:
                                last_topic_id = conversation_memory.last_topic_id
                                
                        is_context_match = (topic_id in active_topics) or (topic_id == last_topic_id)
                    
                    if is_context_match:
                        broken = True
                        broken_ev_id = evidence_id

        # 2. Quebra conversacional (claim contradiction)
        if not broken and analysis and analysis.inferred_claim_targets:
            for target_claim_id in analysis.inferred_claim_targets:
                if target_claim_id in claim_config.get("breakable_by_claim_ids", []):
                    broken = True
                    broken_cl_id = target_claim_id
                    break
                    
        if broken:
            state.status = "broken"
            state.broken_by_evidence_id = broken_ev_id
            state.broken_by_claim_id = broken_cl_id
            state.broken_at = datetime.now()
            has_broken_claims = True
            
            rewards = claim_config.get("reveal_on_break", [])
            
            newly_broken_claims.append({
                "claim_id": state.claim_id,
                "broken_by_evidence_id": broken_ev_id,
                "broken_by_claim_id": broken_cl_id,
                "rewards": rewards
            })
            
            if rewards:
                rewards_to_reveal.extend(rewards)
                
    if has_broken_claims:
        db.flush()
        
    return newly_broken_claims, rewards_to_reveal
