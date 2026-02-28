import json
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.schema_scenario import ScenarioConfig
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SecretModel
)


def load_scenario_from_json(path: str, db: Optional[Session] = None) -> ScenarioModel:
    """
    Loads a scenario from a JSON file, validates it via Pydantic,
    and populates the SQLAlchemy database models.
    Prevents duplication by checking scenario title.
    
    Args:
        path (str): Path to the scenario JSON file.
        db (Session, optional): Existing DB session (useful for tests).
    
    Returns:
        ScenarioModel: The scenario model saved in the database.
    """
    close_session = False

    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Load JSON
        # -------------------------
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # -------------------------
        # 2. Validate with Pydantic
        # -------------------------
        config = ScenarioConfig(**data)

        # -------------------------
        # 3. Check for duplicates
        # -------------------------
        existing = (
            db.query(ScenarioModel)
            .filter(ScenarioModel.title == config.title)
            .first()
        )

        if existing:
            print(f"[loader] Scenario '{config.title}' already exists. Skipping insert.")
            return existing

        # -------------------------
        # 4. Create Scenario
        # -------------------------
        scenario = ScenarioModel(
            title=config.title,
            description=config.description,
            case_summary=config.case_summary
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)

        # Maps for later linking secrets
        suspect_map = {}
        evidence_map = {}

        # -------------------------
        # 5. Insert Suspects
        # -------------------------
        for s in config.suspects:
            suspect = SuspectModel(
                scenario_id=scenario.id,
                name=s.name,
                backstory=s.backstory,
                initial_statement=s.initial_statement,
                final_phrase=s.final_phrase,
                true_timeline=s.true_timeline,
                lies=[lie.dict() for lie in s.lies] if s.lies else None
            )
            db.add(suspect)
            db.commit()
            db.refresh(suspect)

            suspect_map[s.name] = suspect.id

        # -------------------------
        # 6. Insert Evidence
        # -------------------------
        mandatory_evidence_ids = []

        for e in config.evidences:
            evidence = EvidenceModel(
                scenario_id=scenario.id,
                name=e.name,
                description=e.description
            )
            db.add(evidence)
            db.commit()
            db.refresh(evidence)

            evidence_map[e.name] = evidence.id

            if e.is_mandatory:
                mandatory_evidence_ids.append(evidence.id)

        # -------------------------
        # 6.5 Persist verdict rules (T24.5)
        # -------------------------
        scenario.required_evidence_ids = mandatory_evidence_ids
        db.commit()
        db.refresh(scenario)

        # store mandatory evidence IDs inside scenario? (future)
        # for now we keep culprit only

        # -------------------------
        # 7. Set culprit
        # -------------------------
        if config.culprit not in suspect_map:
            raise ValueError(
                f"Culprit '{config.culprit}' not found among suspects."
            )

        scenario.culprit_id = suspect_map[config.culprit]
        db.commit()
        db.refresh(scenario)

        # -------------------------
        # 8. Insert Secrets
        # -------------------------
        for sec in config.secrets:
            if sec.suspect not in suspect_map:
                raise ValueError(
                    f"Secret references unknown suspect '{sec.suspect}'"
                )

            if sec.evidence not in evidence_map:
                raise ValueError(
                    f"Secret references unknown evidence '{sec.evidence}'"
                )

            secret = SecretModel(
                suspect_id=suspect_map[sec.suspect],
                evidence_id=evidence_map[sec.evidence],
                content=sec.content,
                is_core=sec.is_core
            )
            db.add(secret)

        db.commit()

        print(f"[loader] Scenario '{scenario.title}' loaded successfully.")
        return scenario

    finally:
        if close_session:
            db.close()
