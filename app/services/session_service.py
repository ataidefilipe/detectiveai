from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SessionModel,
    SessionSuspectStateModel,
    SuspectModel,
    SecretModel
)


def create_session(scenario_id: int, db: Optional[Session] = None) -> SessionModel:
    """
    Creates a new game session for a given scenario.
    Initializes SessionModel + SessionSuspectState entries for each suspect.

    Args:
        scenario_id (int): ID of the scenario.
        db (Session, optional): Existing SQLAlchemy session.

    Returns:
        SessionModel: The newly created session with suspect states.
    """
    close_session = False

    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Validate scenario exists
        # -------------------------
        scenario = db.query(ScenarioModel).filter(ScenarioModel.id == scenario_id).first()

        if not scenario:
            raise ValueError(f"Scenario with id {scenario_id} does not exist.")

        # -------------------------
        # 2. Create session
        # -------------------------
        session = SessionModel(
            scenario_id=scenario_id,
            status="in_progress"
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # -------------------------
        # 3. Create initial suspect states
        # -------------------------
        suspects = db.query(SuspectModel).filter(SuspectModel.scenario_id == scenario_id).all()

        for suspect in suspects:
            state = SessionSuspectStateModel(
                session_id=session.id,
                suspect_id=suspect.id,
                revealed_secret_ids=[],
                is_closed=False,
                progress=0.0
            )
            db.add(state)

        db.commit()

        # Refresh session to load states
        db.refresh(session)

        print(f"[session] Session {session.id} created for scenario {scenario_id}")
        return session

    finally:
        if close_session:
            db.close()

def get_session_overview(session_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Returns a structured overview of the session:
      - session info
      - scenario summary
      - list of suspects with progress (placeholder logic)
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Load session
        # -------------------------
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

        if not session:
            raise ValueError(f"Session with id {session_id} not found.")

        # -------------------------
        # 2. Load scenario
        # -------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        # -------------------------
        # 3. Load suspects + their session state
        # -------------------------
        suspects = (
            db.query(SuspectModel)
            .filter(SuspectModel.scenario_id == scenario.id)
            .all()
        )

        suspect_states = (
            db.query(SessionSuspectStateModel)
            .filter(SessionSuspectStateModel.session_id == session.id)
            .all()
        )

        # Map suspect_id → state
        state_map = {s.suspect_id: s for s in suspect_states}

        # -------------------------
        # 4. Assemble suspect summaries
        # -------------------------
        suspects_summary = []
        for s in suspects:
            s_state = state_map.get(s.id)

            progress = s_state.progress if s_state else 0.0

            # Pegar o status de 'fechado' (is_closed)
            is_closed = s_state.is_closed if s_state else False

            suspects_summary.append({
                "suspect_id": s.id,
                "name": s.name,
                "progress": progress,
                "is_closed": is_closed
            })

        # -------------------------
        # 5. Assemble final overview
        # -------------------------
        overview = {
            "session": {
                "id": session.id,
                "scenario_id": session.scenario_id,
                "status": session.status,
                "created_at": session.created_at.isoformat()
            },
            "scenario": {
                "title": scenario.title,
                "description": scenario.description,
                "objective": "find_culprit"  # placeholder objective for MVP
            },
            "suspects": suspects_summary
        }

        return overview

    finally:
        if close_session:
            db.close()

def calculate_suspect_progress(
    session_id: int,
    suspect_id: int,
    db: Optional[Session] = None
) -> float:
    """
    Calculates the progress of a suspect in a specific session.

    Progress formula:
        core secrets revealed / total core secrets

    Returns:
        float (0.0 to 1.0)
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Load session state for suspect
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(
                f"Suspect {suspect_id} does not belong to session {session_id}."
            )

        # Load all core secrets of this suspect
        core_secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.is_core == True
        ).all()

        total_core = len(core_secrets)
        if total_core == 0:
            return 1.0  # Suspect has no core secrets → full progress

        # Count how many were revealed
        revealed_core = 0
        for secret in core_secrets:
            if secret.id in state.revealed_secret_ids:
                revealed_core += 1

        progress = revealed_core / total_core

        # Update state.progress automatically (optional but useful)
        state.progress = progress
        db.commit()

        return progress

    finally:
        if close_session:
            db.close()

def get_suspect_state(session_id: int, suspect_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Fetches the progress and closed status of a suspect in a given session.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Fetch the suspect's state for the given session
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(f"Suspect {suspect_id} not part of session {session_id}.")

        return {
            "progress": state.progress,
            "is_closed": state.is_closed
        }
    finally:
        if close_session:
            db.close()





