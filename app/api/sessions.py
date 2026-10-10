from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.api.schemas.chat import PlayerChatInput, PlayerTurnResponse
from app.api.schemas.verdict import AccuseRequest, AccuseResponse
from app.api.schemas.evidence import EvidenceResponse
from app.api.schemas.suspect import SuspectSessionResponse
from app.api.schemas.log import SessionTurnsLogResponse, TurnLogItemSchema, VerdictLogResponse

from app.services.interrogation_turn_service import run_interrogation_turn
from app.services.session_finalize_service import finalize_session
from app.services.session_service import (
    create_session, get_session_overview, get_suspect_state, list_sessions, delete_session
)
from app.services.case_file_service import get_session_case_file
from app.api.schemas.case_file import CaseFileResponse
from app.services.auth_service import get_current_user_optional

from app.infra.db import SessionLocal
from app.infra.db_models import (
    NpcChatMessageModel, SessionModel, SessionSuspectStateModel,
    SessionSuspectTopicStateModel, SessionClaimStateModel, SuspectModel,
    ScenarioModel, EvidenceModel, TurnLogModel, VerdictLogModel, UserModel
)


router = APIRouter()


# -----------------------------
# Request & Response schemas
# -----------------------------
class CreateSessionRequest(BaseModel):
    scenario_id: int


class CreateSessionResponse(BaseModel):
    session_id: int
    scenario_id: int
    status: str
    user_id: Optional[int] = None


class SessionSummaryResponse(BaseModel):
    id: int
    scenario_id: int
    scenario_title: str
    status: str
    result_type: Optional[str] = None
    created_at: Optional[str] = None
    messages_count: int = 0
    user_id: Optional[int] = None


# -----------------------------
# GET /sessions
# -----------------------------
@router.get("/sessions", response_model=List[SessionSummaryResponse])
def api_list_sessions(current_user: Optional[UserModel] = Depends(get_current_user_optional)):
    user_id = current_user.id if current_user else None
    return list_sessions(user_id=user_id)


# -----------------------------
# POST /sessions
# -----------------------------
@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(
    payload: CreateSessionRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    session_data = create_session(payload.scenario_id, user_id=user_id)

    return CreateSessionResponse(
        session_id=session_data["id"],
        scenario_id=session_data["scenario_id"],
        status=session_data["status"],
        user_id=session_data.get("user_id")
    )


# -----------------------------
# DELETE /sessions/{session_id}
# -----------------------------
@router.delete("/sessions/{session_id}")
def api_delete_session(
    session_id: int,
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
):
    try:
        user_id = current_user.id if current_user else None
        delete_session(session_id=session_id, user_id=user_id)
        return {"success": True, "message": f"Sessão {session_id} apagada com sucesso."}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao apagar sessão: {str(e)}")

@router.post(
    "/sessions/{session_id}/suspects/{suspect_id}/messages",
    response_model=PlayerTurnResponse
)
def send_message_to_suspect(session_id: int, suspect_id: int, payload: PlayerChatInput):
    """
    Handles a full interrogation turn atomically.
    """
    db = SessionLocal()
    try:
        result = run_interrogation_turn(
            session_id=session_id,
            suspect_id=suspect_id,
            text=payload.text,
            evidence_id=payload.evidence_id,
            db=db
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.post(
    "/sessions/{session_id}/accuse",
    response_model=AccuseResponse
)
def accuse_session(session_id: int, payload: AccuseRequest):
    """
    Finalizes a session by accusing a suspect with selected evidences.
    """

    db = SessionLocal()
    try:
        # ----------------------------------------
        # 1. Finalize session
        # ----------------------------------------
        result = finalize_session(
            session_id=session_id,
            chosen_suspect_id=payload.suspect_id,
            evidence_ids=payload.evidence_ids,
            motive_key=payload.motive_key,
            db=db
        )

        verdict = result["verdict"]

        # ----------------------------------------
        # 2. Basic description (non-AI)
        # ----------------------------------------
        if verdict["result_type"] == "correct":
            description = (
                "Você identificou corretamente o culpado e apresentou todas "
                "as evidências essenciais."
            )
        elif verdict["result_type"] == "partial":
            reasons = verdict.get("reason_codes", [])
            has_wrong_motive = "wrong_motive" in reasons
            has_missing_evidence = "missing_required_evidence" in reasons
            
            if has_wrong_motive and has_missing_evidence:
                description = (
                    "Você identificou corretamente o culpado, mas escolheu a motivação incorreta "
                    "e deixou passar evidências essenciais."
                )
            elif has_wrong_motive:
                description = (
                    "Você identificou corretamente o culpado, mas escolheu a motivação incorreta."
                )
            elif has_missing_evidence:
                description = (
                    "Você identificou corretamente o culpado, mas deixou passar evidências essenciais."
                )
            else:
                description = (
                    "Você identificou corretamente o culpado, mas a acusação está incompleta."
                )
        else:
            description = (
                "O suspeito acusado não é o verdadeiro culpado."
            )

        # ----------------------------------------
        # 3. Build response
        # ----------------------------------------
        return AccuseResponse(
            session_id=result["session_id"],
            status=result["status"],
            result_type=verdict["result_type"],
            chosen_suspect_id=verdict["chosen_suspect_id"],
            real_culprit_id=verdict["real_culprit_id"],
            required_evidence_ids=verdict["required_evidence_ids"],
            missing_evidence_ids=verdict["missing_evidence_ids"],
            chosen_motive_key=verdict["chosen_motive_key"],
            motive_result=verdict["motive_result"],
            partial_reasons=verdict.get("reason_codes", []),
            description=description
        )

    finally:
        db.close()



# -----------------------------
# NEW: GET /sessions/{session_id}
# -----------------------------

class SessionOverviewResponse(BaseModel):
    session: dict
    scenario: dict
    suspects: list


@router.get("/sessions/{session_id}", response_model=SessionOverviewResponse)
def api_get_session_overview(session_id: int):
    overview = get_session_overview(session_id)

    # get_session_overview já retorna progress e is_closed por suspeito
    return overview

@router.get("/sessions/{session_id}/case-file", response_model=CaseFileResponse)
def api_get_session_case_file(session_id: int):
    """
    Returns the consolidated read-model of the player's discoveries in the given session.
    """
    db = SessionLocal()
    try:
        from app.core.exceptions import NotFoundError
        response = get_session_case_file(session_id, db)
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()

@router.get("/debug/sessions/{session_id}/suspects/{suspect_id}/status")
def get_suspect_status(session_id: int, suspect_id: int):
    db = SessionLocal()
    try:
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise HTTPException(status_code=404, detail="Suspect not found in this session.")

        topic_states = db.query(SessionSuspectTopicStateModel).filter(
            SessionSuspectTopicStateModel.session_id == session_id,
            SessionSuspectTopicStateModel.suspect_id == suspect_id
        ).all()

        return {
            "suspect_id": state.suspect_id,
            "progress": state.progress,
            "is_closed": state.is_closed,
            "stance": state.stance,
            "patience": state.patience,
            "pressure": state.pressure,
            "rapport": state.rapport,
            "last_topic_id": state.last_topic_id,
            "broken_claim_ids": [
                c.claim_id for c in db.query(SessionClaimStateModel).filter(
                    SessionClaimStateModel.session_id == session_id,
                    SessionClaimStateModel.suspect_id == suspect_id,
                    SessionClaimStateModel.status == "broken"
                ).all()
            ],
            "revealed_secret_ids": state.revealed_secret_ids,
            "topic_states": [
                {
                    "topic_id": t.topic_id,
                    "status": t.status,
                    "times_touched": t.times_touched
                }
                for t in topic_states
            ]
        }

    finally:
        db.close()




class ChatMessageResponse(BaseModel):
    id: int
    sender_type: str
    text: str
    evidence_id: int | None
    timestamp: str

@router.get("/sessions/{session_id}/suspects/{suspect_id}/messages",
            response_model=List[ChatMessageResponse])
def get_chat_messages(session_id: int, suspect_id: int):
    """
    Returns the chronological chat history between the player and the suspect
    in the given session.
    """

    db = SessionLocal()

    try:
        # 1. Ensure session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

        # 2. Ensure suspect belongs to scenario of the session
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id,
            SuspectModel.scenario_id == session.scenario_id
        ).first()

        if not suspect:
            raise HTTPException(
                status_code=404,
                detail=f"Suspect {suspect_id} not found in scenario {session.scenario_id}."
            )

        # 3. Load chronological chat history
        messages = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id
        ).order_by(NpcChatMessageModel.timestamp.asc()).all()

        # 4. Serialize for output
        result = [
            ChatMessageResponse(
                id=m.id,
                sender_type=m.sender_type,
                text=m.text,
                evidence_id=m.evidence_id,
                timestamp=m.timestamp.isoformat()
            )
            for m in messages
        ]

        return result

    finally:
        db.close()


@router.get(
    "/sessions/{session_id}/evidences",
    response_model=list[EvidenceResponse]
)
def get_session_evidences(session_id: int):
    db = SessionLocal()
    try:
        # 1. Buscar sessão
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 2. Buscar evidências do cenário
        evidences = db.query(EvidenceModel).filter(
            EvidenceModel.scenario_id == session.scenario_id
        ).all()

        return [
            EvidenceResponse(
                id=e.id,
                name=e.name,
                description=e.description
            )
            for e in evidences
        ]

    finally:
        db.close()

@router.get(
    "/sessions/{session_id}/suspects",
    response_model=list[SuspectSessionResponse]
)
def list_session_suspects(session_id: int):
    db = SessionLocal()
    try:
        # 1. Validar sessão
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 2. Buscar suspeitos do cenário
        suspects = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == session.scenario_id
        ).all()

        # 3. Buscar estados da sessão
        states = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id
        ).all()

        state_map = {s.suspect_id: s for s in states}

        # 4. Montar resposta
        return [
            SuspectSessionResponse(
                suspect_id=s.id,
                name=s.name,
                backstory=s.backstory,
                initial_statement=s.initial_statement
            )
            for s in suspects
        ]

    finally:
        db.close()


@router.get(
    "/sessions/{session_id}/logs/turns",
    response_model=SessionTurnsLogResponse
)
def get_session_turn_logs(
    session_id: int,
    suspect_id: Optional[int] = None,
    include_prompt: bool = False
):
    """
    Returns the analytical turn logs for a session, optionally filtered by suspect.
    """
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        query = db.query(TurnLogModel).filter(TurnLogModel.session_id == session_id)
        if suspect_id is not None:
            query = query.filter(TurnLogModel.suspect_id == suspect_id)

        rows = query.order_by(TurnLogModel.id.asc()).all()

        turns = [
            TurnLogItemSchema(
                id=r.id,
                session_id=r.session_id,
                suspect_id=r.suspect_id,
                turn_number=r.turn_number,
                created_at=r.created_at.isoformat() if r.created_at else "",
                player_message_id=r.player_message_id,
                npc_message_id=r.npc_message_id,
                player_text=r.player_text,
                npc_text=r.npc_text,
                evidence_id=r.evidence_id,
                intent=r.intent,
                move_type=r.move_type,
                primary_topic_id=r.primary_topic_id,
                analysis_provider=r.analysis_provider,
                evidence_effect=r.evidence_effect,
                response_mode=r.response_mode,
                state_before=r.state_before,
                state_after=r.state_after,
                analysis=r.analysis,
                transition=r.transition,
                effects=r.effects,
                ai=r.ai,
                prompt=r.prompt if include_prompt else None,
            )
            for r in rows
        ]

        return SessionTurnsLogResponse(
            session_id=session_id,
            total_turns=len(turns),
            turns=turns
        )
    finally:
        db.close()


@router.get(
    "/sessions/{session_id}/logs/verdict",
    response_model=VerdictLogResponse
)
def get_session_verdict_log(session_id: int):
    """
    Returns the final verdict log for a finished session.
    """
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        verdict_log = db.query(VerdictLogModel).filter(VerdictLogModel.session_id == session_id).first()
        if not verdict_log:
            raise HTTPException(status_code=404, detail=f"No verdict log found for session {session_id}")

        return VerdictLogResponse(
            id=verdict_log.id,
            session_id=verdict_log.session_id,
            scenario_id=verdict_log.scenario_id,
            created_at=verdict_log.created_at.isoformat() if verdict_log.created_at else "",
            result_type=verdict_log.result_type,
            chosen_suspect_id=verdict_log.chosen_suspect_id,
            real_culprit_id=verdict_log.real_culprit_id,
            chosen_motive_key=verdict_log.chosen_motive_key,
            motive_result=verdict_log.motive_result,
            evidence_ids=verdict_log.evidence_ids or [],
            verdict=verdict_log.verdict,
            session_summary=verdict_log.session_summary,
        )
    finally:
        db.close()


