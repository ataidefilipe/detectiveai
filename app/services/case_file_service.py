from typing import List
from sqlalchemy.orm import Session
from app.api.schemas.case_file import (
    CaseFileResponse, 
    CaseFileFactSchema,
    CaseFileEvidenceSchema,
    CaseFileClaimSchema,
    MotiveClueSchema,
    CaseFileSuspectSummarySchema
)
from app.infra.db_models import (
    SessionSuspectStateModel,
    SessionSuspectKnowledgeStateModel,
    SessionSuspectTopicStateModel,
    SessionEvidenceUsageModel,
    SessionClaimStateModel,
    SuspectModel,
    SecretModel,
    EvidenceModel,
    ScenarioModel,
    SessionModel
)
from app.core.exceptions import NotFoundError

def get_session_case_file(session_id: int, db: Session) -> CaseFileResponse:
    """
    Builds a read-model aggregating the known facts of an investigation session.
    """
    states = db.query(SessionSuspectStateModel).filter(
        SessionSuspectStateModel.session_id == session_id
    ).all()

    if not states:
        raise NotFoundError(f"No suspect states found for session {session_id}")

    confirmed_facts_map = {} # (source_type, source_id, suspect_id) -> CaseFileFactSchema
    open_threads_set = set()
    promising_threads_set = set()
    resolved_threads_set = set()
    effective_evidences: List[CaseFileEvidenceSchema] = []
    ineffective_evidences: List[CaseFileEvidenceSchema] = []
    claims_list: List[CaseFileClaimSchema] = []
    suspect_summaries: List[CaseFileSuspectSummarySchema] = []
    motive_clues: List[MotiveClueSchema] = []

    for state in states:
        suspect = db.query(SuspectModel).filter(SuspectModel.id == state.suspect_id).first()
        if not suspect:
            continue
            
        suspect_summaries.append(CaseFileSuspectSummarySchema(
            suspect_id=suspect.id,
            name=suspect.name,
            stance=state.stance,
            patience=state.patience,
            pressure=state.pressure
        ))

        # A) Secrets
        if state.revealed_secret_ids:
            secrets = db.query(SecretModel).filter(
                SecretModel.id.in_(state.revealed_secret_ids)
            ).all()
            for s in secrets:
                evidence = db.query(EvidenceModel).filter(EvidenceModel.id == s.evidence_id).first()
                topic_id = evidence.related_topic_id if evidence else None
                key = ("secret", str(s.id), suspect.id)
                confirmed_facts_map[key] = CaseFileFactSchema(
                    source_type="secret",
                    content=s.content,
                    suspect_id=suspect.id,
                    source_id=str(s.id),
                    topic_id=topic_id
                )
                if topic_id:
                    resolved_threads_set.add(topic_id)
        
        # B) Discovered Knowledge
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
                        topic_id = item.get("topic_id")
                        key = ("knowledge", str(ks.knowledge_id), suspect.id)
                        confirmed_facts_map[key] = CaseFileFactSchema(
                            source_type="knowledge",
                            content=revealed_text,
                            suspect_id=suspect.id,
                            source_id=str(ks.knowledge_id),
                            topic_id=topic_id
                        )
                        if topic_id:
                            promising_threads_set.add(topic_id)

        # C) Discovered Claims (Known or Broken)
        from sqlalchemy import or_
        discovered_claim_states = db.query(SessionClaimStateModel).filter(
            SessionClaimStateModel.session_id == session_id,
            SessionClaimStateModel.suspect_id == suspect.id,
            or_(
                SessionClaimStateModel.status == "broken",
                SessionClaimStateModel.is_revealed == True
            )
        ).all()
        if discovered_claim_states and suspect.claims:
            c_dict = {str(c.get("claim_id")): c for c in suspect.claims}
            for cs in discovered_claim_states:
                claim_item = c_dict.get(str(cs.claim_id))
                if claim_item:
                    is_broken = cs.status == "broken"
                    claims_list.append(CaseFileClaimSchema(
                        claim_id=str(cs.claim_id),
                        statement=claim_item.get("statement", claim_item.get("text", "")),
                        suspect_id=suspect.id,
                        is_broken=is_broken
                    ))
                    
                    if is_broken:
                        topic_id = claim_item.get("topic_id")
                        if topic_id:
                            resolved_threads_set.add(topic_id)
                            
                        # Add to confirmed facts too if they reveal something
                        reveal_texts = claim_item.get("reveal_on_break", [])
                        if reveal_texts:
                            key = ("claim", str(cs.claim_id), suspect.id)
                            confirmed_facts_map[key] = CaseFileFactSchema(
                                source_type="claim",
                                content=" ".join(reveal_texts),
                                suspect_id=suspect.id,
                                source_id=str(cs.claim_id),
                                topic_id=topic_id
                            )
                    else:
                        # Revealed but not broken
                        topic_id = claim_item.get("topic_id")
                        if topic_id:
                            promising_threads_set.add(topic_id)

        # D) Evidence Usages
        usages = db.query(SessionEvidenceUsageModel).filter(
            SessionEvidenceUsageModel.session_id == session_id,
            SessionEvidenceUsageModel.suspect_id == suspect.id
        ).all()
        
        for usage in usages:
            evidence = db.query(EvidenceModel).filter(EvidenceModel.id == usage.evidence_id).first()
            if evidence:
                ev_schema = CaseFileEvidenceSchema(
                    evidence_id=evidence.id,
                    evidence_code=evidence.evidence_code,
                    name=evidence.name,
                    suspect_id=suspect.id
                )
                # Usar effect_type se disponível, senão fallback para was_effective
                if usage.effect_type and usage.effect_type in ("revealed_secret", "broke_claim", "motive_clue"):
                    effective_evidences.append(ev_schema)
                    if evidence.related_topic_id:
                        resolved_threads_set.add(evidence.related_topic_id)
                elif usage.was_effective:
                    effective_evidences.append(ev_schema)
                    if evidence.related_topic_id:
                        resolved_threads_set.add(evidence.related_topic_id)
                else:
                    ineffective_evidences.append(ev_schema)

        # E) Open Threads (Touched Topics)
        topic_states = db.query(SessionSuspectTopicStateModel).filter(
            SessionSuspectTopicStateModel.session_id == session_id,
            SessionSuspectTopicStateModel.suspect_id == suspect.id,
            SessionSuspectTopicStateModel.times_touched > 0
        ).all()
        for ts in topic_states:
            open_threads_set.add(ts.topic_id)
            
    # Múltiplos motives clues
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    scenario = db.query(ScenarioModel).filter(ScenarioModel.id == session_obj.scenario_id).first() if session_obj else None
    
    if scenario and scenario.motive_clues:
        for mc in scenario.motive_clues:
            revealed_by = mc.get("revealed_by", {})
            req_suspect_id = revealed_by.get("suspect_id")
            req_evidence_code = revealed_by.get("evidence_code")
            
            is_revealed = False
            susp_id_found = None
            
            if req_suspect_id and req_evidence_code:
                susp = db.query(SuspectModel).filter(SuspectModel.scenario_id == scenario.id, SuspectModel.suspect_code == req_suspect_id).first()
                if susp:
                    susp_id_found = susp.id
                    ev = db.query(EvidenceModel).filter(EvidenceModel.scenario_id == scenario.id, EvidenceModel.evidence_code == req_evidence_code).first()
                    if ev:
                        usage = db.query(SessionEvidenceUsageModel).filter(
                            SessionEvidenceUsageModel.session_id == session_id,
                            SessionEvidenceUsageModel.suspect_id == susp.id,
                            SessionEvidenceUsageModel.evidence_id == ev.id
                        ).first()
                        # T4.1: Exigir efeito significativo, não apenas apresentação
                        if usage:
                            if usage.effect_type and usage.effect_type in (
                                "motive_clue", "revealed_secret", "broke_claim"
                            ):
                                is_revealed = True
                            elif usage.was_effective:
                                # Fallback para bancos sem effect_type
                                is_revealed = True
                            
            if is_revealed and susp_id_found:
                motive_clues.append(MotiveClueSchema(
                    id=mc.get("id"),
                    motive_key=mc.get("motive_key"),
                    topic_id=mc.get("topic_id"),
                    content=mc.get("content"),
                    revealed_by_suspect_id=susp_id_found,
                    revealed_by_evidence_code=req_evidence_code
                ))

    return CaseFileResponse(
        session_id=session_id,
        confirmed_facts=list(confirmed_facts_map.values()),
        open_threads=sorted(list(open_threads_set)),
        promising_threads=sorted(list(promising_threads_set - resolved_threads_set)),
        resolved_threads=sorted(list(resolved_threads_set)),
        effective_evidences=effective_evidences,
        ineffective_evidences=ineffective_evidences,
        claims=claims_list,
        suspect_summaries=suspect_summaries,
        motive_clues=motive_clues
    )
