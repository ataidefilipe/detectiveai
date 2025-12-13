from fastapi import APIRouter, HTTPException
from typing import List

from app.infra.db import SessionLocal
from app.infra.db_models import ScenarioModel, SuspectModel, EvidenceModel
from app.api.schemas.scenario import (
    ScenarioListItem,
    ScenarioDetailResponse
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# -----------------------------
# GET /scenarios
# -----------------------------
@router.get("", response_model=List[ScenarioListItem])
def list_scenarios():
    db = SessionLocal()
    try:
        scenarios = db.query(ScenarioModel).all()

        return [
            ScenarioListItem(
                id=s.id,
                title=s.title,
                description=s.description
            )
            for s in scenarios
        ]
    finally:
        db.close()


# -----------------------------
# GET /scenarios/{id} (opcional)
# -----------------------------
@router.get("/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario_detail(scenario_id: int):
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == scenario_id
        ).first()

        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        suspects = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario_id
        ).all()

        evidences = db.query(EvidenceModel).filter(
            EvidenceModel.scenario_id == scenario_id
        ).all()

        return ScenarioDetailResponse(
            id=scenario.id,
            title=scenario.title,
            description=scenario.description,
            suspects=[
                {"id": s.id, "name": s.name}
                for s in suspects
            ],
            evidences=[
                {
                    "id": e.id,
                    "name": e.name,
                    "description": e.description,
                    "is_mandatory": e.id in (scenario.required_evidence_ids or [])
                }
                for e in evidences
            ]
        )

    finally:
        db.close()
