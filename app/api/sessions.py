from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from app.api.schemas.chat import PlayerChatInput
from app.api.schemas.verdict import AccuseRequest, AccuseResponse
from app.api.schemas.evidence import EvidenceResponse
from app.api.schemas.suspect import SuspectSessionResponse

from app.services.interrogation_turn_service import run_interrogation_turn
from app.services.session_finalize_service import finalize_session
from app.services.session_service import create_session, get_session_overview, get_suspect_state

from app.infra.db import SessionLocal
from app.infra.db_models import NpcChatMessageModel, SessionModel, SessionSuspectStateModel, SuspectModel, ScenarioModel, EvidenceModel


router = APIRouter()


# -----------------------------
# Request schema
# -----------------------------
class CreateSessionRequest(BaseModel):
    scenario_id: int


# -----------------------------
# Response schema
# -----------------------------
class CreateSessionResponse(BaseModel):
    session_id: int
    scenario_id: int
    status: str


# -----------------------------
# POST /sessions
# -----------------------------
@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(payload: CreateSessionRequest):
    session_data = create_session(payload.scenario_id)

    return CreateSessionResponse(
        session_id=session_data["id"],
        scenario_id=session_data["scenario_id"],
        status=session_data["status"]
    )

@router.post("/sessions/{session_id}/suspects/{suspect_id}/messages")
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
    except Exception as e:
        db.rollback()
        raise e
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
            description = (
                "Você identificou corretamente o culpado, mas deixou passar "
                "evidências essenciais."
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

@router.get("/sessions/{session_id}/suspects/{suspect_id}/status")
def get_suspect_status(session_id: int, suspect_id: int):
    db = SessionLocal()
    try:
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise HTTPException(status_code=404, detail="Suspect not found in this session.")

        return {
            "suspect_id": state.suspect_id,
            "progress": state.progress,
            "is_closed": state.is_closed
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

        # 3. Mapear obrigatórias
        mandatory_ids = session.scenario.required_evidence_ids

        return [
            EvidenceResponse(
                id=e.id,
                name=e.name,
                description=e.description,
                is_mandatory=e.id in mandatory_ids
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
                initial_statement=s.initial_statement,
                progress=state_map[s.id].progress if s.id in state_map else 0.0,
                is_closed=state_map[s.id].is_closed if s.id in state_map else False
            )
            for s in suspects
        ]

    finally:
        db.close()

