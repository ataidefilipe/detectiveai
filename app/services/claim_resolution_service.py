from typing import List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.infra.db_models import SessionClaimStateModel, SuspectModel, EvidenceModel
from app.api.schemas.chat import MessageAnalysisResult

def resolve_broken_claims(
    session_id: int,
    suspect_id: int,
    evidence_id: Optional[int] = None,
    analysis: Optional[MessageAnalysisResult] = None,
    db: Session = None
) -> Tuple[List[str], List[str]]:
    """
    Avalia se alguma claim do suspeito deve ser quebrada no turno atual.
    
    Returns:
        Um tupla contendo:
        1. Lista de `claim_id` recém quebradas.
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
    
    for state in claim_states:
        claim_config = config_claims.get(state.claim_id)
        if not claim_config:
            continue
            
        broken = False
        broken_ev_id = None
        broken_cl_id = None
        
        # 1. Quebra por evidência objetiva
        if evidence_id and claim_config.get("breakable_by_evidence_ids"):
            evidence = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
            if evidence and evidence.name in claim_config["breakable_by_evidence_ids"]:
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
            
            newly_broken_claims.append(state.claim_id)
            if claim_config.get("reveal_on_break"):
                rewards_to_reveal.extend(claim_config["reveal_on_break"])
                
    if newly_broken_claims:
        db.flush()
        
    return newly_broken_claims, rewards_to_reveal
