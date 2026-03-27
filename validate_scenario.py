#!/usr/bin/env python3
"""
CONTENT-001: validate_scenario.py

CLI script to validate a scenario JSON file against the ScenarioConfig Pydantic schema
and all referential integrity rules — without starting the server or accessing the DB.

Usage:
    python validate_scenario.py scenarios/piloto.json

Exit codes:
    0 — valid scenario
    1 — one or more validation errors found
"""
import sys
import json
from typing import List

try:
    from pydantic import ValidationError
    from app.domain.schema_scenario import ScenarioConfig
except ImportError as e:
    print(f"[ERROR] Could not import project modules: {e}")
    print("Make sure you are running from the project root and the virtual environment is active.")
    sys.exit(1)


def validate_scenario(path: str) -> List[str]:
    """
    Validates a scenario JSON file.
    Returns a list of error messages (empty if valid).
    """
    errors = []

    # 1. Load JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except json.JSONDecodeError as e:
        return [f"Invalid JSON at {path}: {e}"]

    # 2. Pydantic validation
    try:
        config = ScenarioConfig(**data)
    except ValidationError as e:
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            errors.append(f"[Schema] {loc}: {err['msg']}")
        return errors  # Can't do referential checks without a valid config

    # 3. True motive key
    if config.true_motive_key and config.motives:
        valid_motive_keys = [m.key for m in config.motives]
        if config.true_motive_key not in valid_motive_keys:
            errors.append(
                f"[Motive] true_motive_key '{config.true_motive_key}' not found in motives list"
            )

    # 4. Uniqueness
    suspect_ids = [s.id for s in config.suspects]
    if len(suspect_ids) != len(set(suspect_ids)):
        seen = set()
        for sid in suspect_ids:
            if sid in seen:
                errors.append(f"[Uniqueness] Duplicate suspect id: '{sid}'")
            seen.add(sid)

    evidence_ids = [e.id for e in config.evidences]
    if len(evidence_ids) != len(set(evidence_ids)):
        seen = set()
        for eid in evidence_ids:
            if eid in seen:
                errors.append(f"[Uniqueness] Duplicate evidence id: '{eid}'")
            seen.add(eid)

    # 5. Referential integrity
    valid_evidence_ids = {e.id for e in config.evidences}
    valid_topic_ids = {t.id for t in config.topics} if config.topics else set()

    for e in config.evidences:
        if e.related_topic_id and e.related_topic_id not in valid_topic_ids:
            errors.append(
                f"[Reference] Evidence '{e.id}': related_topic_id '{e.related_topic_id}' not found in topics"
            )

    for s in config.suspects:
        if s.lies:
            for lie in s.lies:
                if lie.topic_id not in valid_topic_ids:
                    errors.append(
                        f"[Reference] Suspect '{s.id}', Lie '{lie.id}': topic_id '{lie.topic_id}' not found in topics"
                    )
                if lie.broken_by_evidence not in valid_evidence_ids:
                    errors.append(
                        f"[Reference] Suspect '{s.id}', Lie '{lie.id}': broken_by_evidence '{lie.broken_by_evidence}' not found in evidences"
                    )
        if s.knowledge:
            for k in s.knowledge:
                if k.topic_id not in valid_topic_ids:
                    errors.append(
                        f"[Reference] Suspect '{s.id}', KnowledgeItem '{k.id}': topic_id '{k.topic_id}' not found in topics"
                    )

    for sec in config.secrets:
        if sec.suspect not in set(suspect_ids):
            errors.append(f"[Reference] Secret references unknown suspect '{sec.suspect}'")
        if sec.evidence not in valid_evidence_ids:
            errors.append(f"[Reference] Secret references unknown evidence '{sec.evidence}'")

    # 6. Culprit exists
    if config.culprit not in set(suspect_ids):
        errors.append(f"[Culprit] culprit '{config.culprit}' not found in suspects list")

    # 7. required_broken_lie_ids (VERD-002)
    if config.required_broken_lie_ids:
        all_lie_ids = {
            lie.id
            for s in config.suspects
            if s.lies
            for lie in s.lies
        }
        for lie_id in config.required_broken_lie_ids:
            if lie_id not in all_lie_ids:
                errors.append(
                    f"[Reference] required_broken_lie_ids: lie '{lie_id}' not found in any suspect's lies"
                )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_scenario.py <path_to_scenario.json>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Validating: {path}")

    errors = validate_scenario(path)

    if not errors:
        print("✅ Scenario is valid!")
        sys.exit(0)
    else:
        print(f"❌ Found {len(errors)} error(s):\n")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
