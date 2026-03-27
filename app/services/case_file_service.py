from typing import List
from sqlalchemy.orm import Session
from app.api.schemas.case_file import (
    CaseFileResponse, 
    CaseFileSuspectEntry, 
    SecretEntry, 
    KnowledgeEntry, 
    BrokenLieEntry, 
    EffectiveEvidenceEntry
)
from app.infra.db_models import (
    SessionSuspectStateModel,
    SessionSuspectKnowledgeStateModel,
    SessionEvidenceUsageModel,
    SuspectModel,
    SecretModel,
    EvidenceModel
)
from app.core.exceptions import NotFoundError

def get_session_case_file(session_id: int, db: Session) -> CaseFileResponse:
    """
    Builds a read-model aggregating the known facts of an investigation session.
    It resolves state IDs against original JSON/DB entities to return text data.
    """
    # 1. Fetch all states from the session
    states = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id
    ).all()

    if not states:
        raise NotFoundError(f"No suspect states found for session {session_id}")

    suspect_entries: List[CaseFileSuspectEntry] = []

    for state in states:
        # Load human readable suspect
        suspect = db.query(SuspectModel).filter(SuspectModel.id == state.suspect_id).first()
        if not suspect:
            continue
            
        # A) Resolve Revealed Secrets
        revealed_secrets_list = []
        if state.revealed_secret_ids:
            secrets = db.query(SecretModel).filter(
                SecretModel.id.in_(state.revealed_secret_ids)
            ).all()
            for s in secrets:
                revealed_secrets_list.append(SecretEntry(
                    id=s.id,
                    content=s.content,
                    is_core=s.is_core
                ))
        
        # B) Resolve Discovered Knowledge
        knowledge_list = []
        k_states = db.query(SessionSuspectKnowledgeStateModel).filter(
            SessionSuspectKnowledgeStateModel.session_id == session_id,
            SessionSuspectKnowledgeStateModel.suspect_id == suspect.id,
            SessionSuspectKnowledgeStateModel.max_revealed_depth > 0
        ).all()
        
        if suspect.knowledge_items:
            k_dict = {str(k.get("id")): k for k in suspect.knowledge_items}
            for ks in k_states:
                item = k_dict.get(ks.knowledge_id)
                if item:
                    layers = item.get("content_layers", [])
                    depth = min(ks.max_revealed_depth, len(layers))
                    if depth > 0:
                        revealed_text = " ".join(layers[:depth])
                        knowledge_list.append(KnowledgeEntry(
                            id=ks.knowledge_id,
                            revealed_text=revealed_text
                        ))

        # C) Resolve Broken Lies
        broken_lies_list = []
        if state.broken_lie_ids and suspect.lies:
            l_dict = {str(l.get("id")): l for l in suspect.lies}
            for lie_id in state.broken_lie_ids:
                lie_item = l_dict.get(str(lie_id))
                if lie_item:
                    broken_lies_list.append(BrokenLieEntry(
                        id=str(lie_id),
                        statement=lie_item.get("statement", "")
                    ))

        # D) Resolve Effective Evidences
        evidence_list = []
        effective_usages = db.query(SessionEvidenceUsageModel).filter(
            SessionEvidenceUsageModel.session_id == session_id,
            SessionEvidenceUsageModel.suspect_id == suspect.id,
            SessionEvidenceUsageModel.was_effective == True
        ).all()
        
        for usage in effective_usages:
            evidence = db.query(EvidenceModel).filter(EvidenceModel.id == usage.evidence_id).first()
            if evidence:
                evidence_list.append(EffectiveEvidenceEntry(
                    id=evidence.id,
                    name=evidence.name
                ))

        # Assemble suspect grouping
        suspect_entries.append(CaseFileSuspectEntry(
            suspect_id=suspect.id,
            name=suspect.name,
            revealed_secrets=revealed_secrets_list,
            discovered_knowledge=knowledge_list,
            broken_lies=broken_lies_list,
            effective_evidences=evidence_list
        ))

    return CaseFileResponse(
        session_id=session_id,
        suspects=suspect_entries
    )
