from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from typesafe_sdk import Noul, Score

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SessionEvidenceUsageModel,
    SessionSuspectStateModel,
    SessionClaimStateModel
)
from app.core.exceptions import NotFoundError, RuleViolationError
from app.core.telemetry import telemetry_logger
from app.core.config import settings
import json


def evaluate_narrative_theory(
    narrative_theory: Optional[str],
    scenario: ScenarioModel,
    real_culprit_name: Optional[str] = None,
    true_motive_label: Optional[str] = None,
    provider: Optional[str] = None,
) -> Tuple[Optional[float], Optional[List[str]]]:
    """
    EPIC 4 (Tarefa 4.1) — Avalia a reconstrução narrativa livre do detetive
    contra a verdade objetiva do caso (case_summary, culpado e motivo).
    Retorna (theory_score_0_to_1, matched_elements) ou (None, None) se vazio.
    """
    if not narrative_theory or not narrative_theory.strip():
        return None, None

    from app.services.typesafe_client import evaluate_system_one, resolve_typesafe_api_key

    use_jev = provider == "jev" or (provider is None and bool(resolve_typesafe_api_key()))
    if use_jev:
        questions = {
            "culprit_identified": Noul(
                instructions="A teoria do jogador identifica corretamente o verdadeiro culpado pelo crime?"
            ),
            "motive_explained": Noul(
                instructions="A teoria explica corretamente o motivo real (true_motive) do crime?"
            ),
            "method_and_opportunity": Noul(
                instructions="A teoria descreve de forma compatível como e em que circunstâncias o crime ocorreu?"
            ),
            "alibi_or_coverup": Noul(
                instructions="A teoria identifica a tentativa de ocultação, álibi falso ou adulteração ligada ao caso?"
            ),
            "coherence": Score(
                instructions="Quão aderente e completa é a reconstrução do jogador em relação ao case_summary real?",
                criteria=["totalmente errada", "parcial / superficial", "boa / consistente", "exata e completa"],
            ),
        }
        state = {
            "player_narrative_theory": narrative_theory.strip(),
            "ground_truth_case_summary": scenario.case_summary,
            "real_culprit_name": real_culprit_name,
            "true_motive": true_motive_label or scenario.true_motive_key,
        }
        res = evaluate_system_one(state=state, questions=questions)
        if res.ok and res.response is not None:
            nouls = getattr(res.response, "nouls", {}) or {}
            scores = getattr(res.response, "scores", {}) or {}
            matched = [
                k for k in ("culprit_identified", "motive_explained", "method_and_opportunity", "alibi_or_coverup")
                if k in nouls and nouls[k].noul >= 0.65
            ]
            raw_score = float(scores["coherence"].score) if "coherence" in scores else 0.0
            normalized = round(max(0.0, min(1.0, raw_score / 3.0)), 4)
            return normalized, matched

    # Fallback determinístico sem Jev
    theory_lower = narrative_theory.lower()
    matched_fallback: List[str] = []
    if real_culprit_name and any(part in theory_lower for part in real_culprit_name.lower().split() if len(part) > 3):
        matched_fallback.append("culprit_identified")
    if true_motive_label and any(w in theory_lower for w in true_motive_label.lower().split() if len(w) > 4):
        matched_fallback.append("motive_explained")
    if scenario.case_summary:
        summary_words = {w.strip(".,;:!?") for w in scenario.case_summary.lower().split() if len(w) > 5}
        hits = sum(1 for w in summary_words if w in theory_lower)
        if hits >= 2:
            matched_fallback.append("method_and_opportunity")

    score_fallback = round(len(matched_fallback) / 3.0, 4)
    return score_fallback, matched_fallback


def evaluate_verdict(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    motive_key: str,
    db: Optional[Session] = None,
    narrative_theory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates the final verdict of a session.

    Rules:
    - If chosen suspect is NOT the real culprit → result_type = "wrong"
    - If chosen suspect IS the real culprit:
        - If all required evidences are present → "correct"
        - Else → "partial"

    Returns:
        Dict with:
            - result_type
            - missing_evidence_ids
            - required_evidence_ids
            - chosen_suspect_id
            - real_culprit_id
            - chosen_motive_key
            - motive_result
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ----------------------------------------
        # 1. Load session
        # ----------------------------------------
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise NotFoundError(f"Session {session_id} not found.")

        # ----------------------------------------
        # 2. Load scenario
        # ----------------------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        if not scenario:
            raise NotFoundError(
                f"Scenario {session.scenario_id} not found for session {session_id}."
            )

        real_culprit_id = scenario.culprit_id
        required_evidence_ids = scenario.required_evidence_ids or []
        required_broken_claim_ids = scenario.required_broken_claim_ids or []
        true_motive_key = scenario.true_motive_key
        
        # Validate motive exists in scenario options
        if scenario.motive_options:
            valid_motive_keys = [m.get("key") for m in scenario.motive_options]
            if motive_key not in valid_motive_keys:
                raise NotFoundError(f"Motive {motive_key} is not valid for this scenario.")
                
        # Validate motive clue was discovered
        if settings.REQUIRE_DISCOVERED_MOTIVE and scenario.motive_clues:
            from app.services.case_file_service import get_session_case_file
            case_file = get_session_case_file(session_id, db)
            discovered_motive_keys = {mc.motive_key for mc in case_file.motive_clues}
            
            if motive_key not in discovered_motive_keys:
                raise RuleViolationError(f"Motive {motive_key} was not discovered in the case file.")

        # ----------------------------------------
        # 2.5. Validate User Input (B2)
        # ----------------------------------------
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == chosen_suspect_id,
            SuspectModel.scenario_id == scenario.id
        ).first()

        if not suspect:
            raise NotFoundError(f"Suspect {chosen_suspect_id} not found in scenario {scenario.id}.")

        provided = list(set(evidence_ids or []))
        
        if provided:
            valid_evidences = db.query(EvidenceModel).filter(
                EvidenceModel.id.in_(provided),
                EvidenceModel.scenario_id == scenario.id
            ).all()

            if len(valid_evidences) != len(provided):
                raise NotFoundError(f"One or more evidence ids are invalid or do not belong to scenario {scenario.id}.")

            # ----------------------------------------
            # 2.6. Validate Evidence Usage (B3)
            # ----------------------------------------
            # T9: Changed to session-level (removed suspect_id == chosen_suspect_id).
            # T10: Added requirement for was_effective == True.
            used_evidences = db.query(SessionEvidenceUsageModel.evidence_id).filter(
                SessionEvidenceUsageModel.session_id == session_id,
                SessionEvidenceUsageModel.was_effective == True,
                SessionEvidenceUsageModel.evidence_id.in_(provided)
            ).all()
            used_evidence_ids = {row[0] for row in used_evidences}

            for ev_id in provided:
                if ev_id not in used_evidence_ids:
                    raise RuleViolationError(f"Evidence {ev_id} was not used effectively during the session.")

        # ----------------------------------------
        # 3. Assess Motive Result, Theory & Reason Codes
        # ----------------------------------------
        motive_result = "correct" if motive_key == true_motive_key else "wrong"
        real_culprit_obj = db.query(SuspectModel).filter(SuspectModel.id == real_culprit_id).first() if real_culprit_id else None
        true_motive_label = None
        if scenario.motive_options and true_motive_key:
            for m in scenario.motive_options:
                if m.get("key") == true_motive_key:
                    true_motive_label = m.get("label")
                    break
        theory_score, theory_matched_elements = evaluate_narrative_theory(
            narrative_theory=narrative_theory,
            scenario=scenario,
            real_culprit_name=real_culprit_obj.name if real_culprit_obj else None,
            true_motive_label=true_motive_label,
        )
        
        # T11: Reason Codes
        reason_codes = []
        missing_claim_ids = []

        # ----------------------------------------
        # 4. Wrong culprit → immediate fail
        # ----------------------------------------
        if chosen_suspect_id != real_culprit_id:
            reason_codes.append("wrong_suspect")
            
            result_dict = {
                "result_type": "wrong",
                "missing_evidence_ids": required_evidence_ids,
                "required_evidence_ids": required_evidence_ids,
                "chosen_suspect_id": chosen_suspect_id,
                "real_culprit_id": real_culprit_id,
                "chosen_motive_key": motive_key,
                "motive_result": motive_result,
                "reason_codes": reason_codes,
                "missing_claim_ids": missing_claim_ids,
                "theory_score": theory_score,
                "theory_matched_elements": theory_matched_elements,
            }
            telemetry_logger.info(json.dumps({
                "event": "session_verdict",
                "session_id": session_id,
                "scenario_id": scenario.id,
                **result_dict
            }))
            return result_dict

        # ----------------------------------------
        # 5. Culprit correct → check evidences, motive & required claims
        # ----------------------------------------
        if motive_result == "wrong":
            reason_codes.append("wrong_motive")
            
        required = set(required_evidence_ids)
        missing = list(required - set(provided))
        
        if missing:
            reason_codes.append("missing_required_evidence")

        # VERD-002: Check required broken claims
        if required_broken_claim_ids:
            broken_claims = db.query(SessionClaimStateModel).filter(
                SessionClaimStateModel.session_id == session_id,
                SessionClaimStateModel.suspect_id == chosen_suspect_id,
                SessionClaimStateModel.status == "broken"
            ).all()
            broken_claim_ids = [c.claim_id for c in broken_claims] if broken_claims else []
            missing_claim_ids = [c_id for c_id in required_broken_claim_ids if c_id not in broken_claim_ids]
            if missing_claim_ids:
                reason_codes.append("missing_required_claim")

        if not reason_codes:
            result_type = "correct"
        else:
            result_type = "partial"

        result_dict = {
            "result_type": result_type,
            "missing_evidence_ids": missing,
            "required_evidence_ids": required_evidence_ids,
            "chosen_suspect_id": chosen_suspect_id,
            "real_culprit_id": real_culprit_id,
            "chosen_motive_key": motive_key,
            "motive_result": motive_result,
            "reason_codes": reason_codes,
            "missing_claim_ids": missing_claim_ids,
            "theory_score": theory_score,
            "theory_matched_elements": theory_matched_elements,
        }
        
        telemetry_logger.info(json.dumps({
            "event": "session_verdict",
            "session_id": session_id,
            "scenario_id": scenario.id,
            **result_dict
        }))

        return result_dict

    finally:
        if close_session:
            db.close()
