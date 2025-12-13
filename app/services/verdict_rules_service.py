from typing import List
from sqlalchemy.orm import Session
from app.infra.db_models import ScenarioModel
from app.infra.db import SessionLocal


def get_required_evidences_for_scenario(
    scenario_id: int,
    db: Session | None = None
) -> List[int]:
    """
    Returns the list of mandatory evidence IDs for a scenario.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == scenario_id
        ).first()

        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found.")

        return scenario.required_evidence_ids or []

    finally:
        if close_session:
            db.close()
