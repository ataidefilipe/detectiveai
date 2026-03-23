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
from app.core.exceptions import DomainError


def load_scenario_from_json(path: str, db: Optional[Session] = None) -> ScenarioModel:
    """
    Loads a scenario from a JSON file, validates it via Pydantic,
    and populates the SQLAlchemy database models.
    Prevents duplication by checking scenario title explicitly avoiding any 
    updates to already inserted scenarios (idempotent 'insert-if-not-exists').
    
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

    data = {}
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
            .filter(ScenarioModel.scenario_code == config.scenario_code)
            .first()
        )

        if existing:
            print(f"[loader] Cenário '{config.scenario_code}' já existe. Ignorando atualização (para forçar o update, delete o arquivo game.db).")
            return existing

        # -------------------------
        # 3.5 Validate True Motive
        # -------------------------
        if config.true_motive_key and config.motives:
            valid_motive_keys = [m.key for m in config.motives]
            if config.true_motive_key not in valid_motive_keys:
                raise DomainError(f"true_motive_key '{config.true_motive_key}' is not in motives list.")
                
        # -------------------------
        # 3.6 Validações Estruturais de Fiações Cruzadas (SESS-003)
        # -------------------------
        valid_evidence_ids = {e.id for e in config.evidences}
        valid_topic_ids = {t.id for t in config.topics} if config.topics else set()
        
        for e in config.evidences:
            if e.related_topic_id and e.related_topic_id not in valid_topic_ids:
                raise DomainError(f"Evidence '{e.id}' references unknown related_topic_id '{e.related_topic_id}'")
        
        for s in config.suspects:
            if s.lies:
                for lie in s.lies:
                    if lie.topic_id not in valid_topic_ids:
                        raise DomainError(f"Lie '{lie.id}' for '{s.id}' references unknown topic_id '{lie.topic_id}'")
                    if lie.broken_by_evidence not in valid_evidence_ids:
                        raise DomainError(f"Lie '{lie.id}' for '{s.id}' references unknown broken_by_evidence '{lie.broken_by_evidence}'")
            if s.knowledge:
                for k in s.knowledge:
                    if k.topic_id not in valid_topic_ids:
                        raise DomainError(f"KnowledgeItem '{k.id}' for suspect '{s.id}' references unknown topic_id '{k.topic_id}'")

        # -------------------------
        # 4. Create Scenario
        # -------------------------
        scenario = ScenarioModel(
            scenario_code=config.scenario_code,
            title=config.title,
            description=config.description,
            case_summary=config.case_summary,
            topics=[t.model_dump() for t in config.topics] if config.topics else [],
            motive_options=[m.model_dump() for m in config.motives] if config.motives else [],
            true_motive_key=config.true_motive_key
        )
        db.add(scenario)
        db.flush()
        db.refresh(scenario)

        # Maps for later linking secrets
        suspect_map = {}
        evidence_map = {}

        # -------------------------
        # 5. Insert Suspects
        # -------------------------
        evidence_name_map = {e.id: e.name for e in config.evidences}

        for s in config.suspects:
            lies_dicts = []
            if s.lies:
                for lie in s.lies:
                    lie_dict = lie.dict()
                    lie_dict['broken_by_evidence'] = evidence_name_map.get(lie.broken_by_evidence, lie.broken_by_evidence)
                    lies_dicts.append(lie_dict)

            suspect = SuspectModel(
                scenario_id=scenario.id,
                name=s.name,
                backstory=s.backstory,
                personality=s.personality,
                internal_note=s.internal_note,
                initial_statement=s.initial_statement,
                final_phrase=s.final_phrase,
                true_timeline=s.true_timeline,
                lies=lies_dicts if lies_dicts else None,
                knowledge_items=[k.model_dump() for k in s.knowledge] if s.knowledge else []
            )
            db.add(suspect)
            db.flush()
            db.refresh(suspect)

            suspect_map[s.id] = suspect.id

        # -------------------------
        # 6. Insert Evidence
        # -------------------------
        mandatory_evidence_ids = []

        for e in config.evidences:
            evidence = EvidenceModel(
                scenario_id=scenario.id,
                name=e.name,
                description=e.description,
                internal_note=e.internal_note,
                related_topic_id=e.related_topic_id
            )
            db.add(evidence)
            db.flush()
            db.refresh(evidence)

            evidence_map[e.id] = evidence.id

            if e.is_mandatory:
                mandatory_evidence_ids.append(evidence.id)

        # -------------------------
        # 6.5 Persist verdict rules (T24.5)
        # -------------------------
        scenario.required_evidence_ids = mandatory_evidence_ids
        db.flush()
        db.refresh(scenario)

        # store mandatory evidence IDs inside scenario? (future)
        # for now we keep culprit only

        # -------------------------
        # 7. Set culprit
        # -------------------------
        if config.culprit not in suspect_map:
            raise DomainError(
                f"Culprit '{config.culprit}' not found among suspects."
            )

        scenario.culprit_id = suspect_map[config.culprit]
        db.flush()
        db.refresh(scenario)

        # -------------------------
        # 8. Insert Secrets
        # -------------------------
        for sec in config.secrets:
            if sec.suspect not in suspect_map:
                raise DomainError(
                    f"Secret references unknown suspect '{sec.suspect}'"
                )

            if sec.evidence not in evidence_map:
                raise DomainError(
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
    except Exception as e:
        db.rollback()
        print(f"[loader] Transaction failed! Rolling back scenario '{data.get('title', 'Unknown')}'. Reason: {e}")
        raise

    finally:
        if close_session:
            db.close()
