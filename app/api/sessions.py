from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.session_service import create_session, get_session_overview

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
    try:
        session = create_session(payload.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateSessionResponse(
        session_id=session.id,
        scenario_id=session.scenario_id,
        status=session.status
    )


# -----------------------------
# NEW: GET /sessions/{session_id}
# -----------------------------

class SessionOverviewResponse(BaseModel):
    session: dict
    scenario: dict
    suspects: list


@router.get("/sessions/{session_id}", response_model=SessionOverviewResponse)
def api_get_session_overview(session_id: int):
    try:
        overview = get_session_overview(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return overview