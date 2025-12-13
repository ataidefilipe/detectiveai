from pathlib import Path
from sqlalchemy.orm import Session

from app.infra.db import init_db, SessionLocal
from app.infra.db_models import ScenarioModel
from app.services.scenario_loader import load_scenario_from_json


SCENARIOS_DIR = Path("scenarios")


def bootstrap_game():
    """
    Bootstraps the game environment on API startup.

    Responsibilities:
    - Initialize database tables
    - Load scenario JSON files if no scenario exists
    - Ensure idempotency (safe to run multiple times)
    """

    # 1. Ensure DB schema exists
    init_db()

    db: Session = SessionLocal()
    try:
        # 2. Check if any scenario already exists
        existing = db.query(ScenarioModel).first()
        if existing:
            print("[bootstrap] Scenario(s) already present. Skipping load.")
            return

        # 3. Load all scenario JSON files
        if not SCENARIOS_DIR.exists():
            print("[bootstrap] No scenarios directory found. Skipping.")
            return

        json_files = list(SCENARIOS_DIR.glob("*.json"))

        if not json_files:
            print("[bootstrap] No scenario JSON files found. Skipping.")
            return

        print(f"[bootstrap] Loading {len(json_files)} scenario(s)...")

        for path in json_files:
            load_scenario_from_json(str(path), db=db)

        print("[bootstrap] Scenario bootstrap completed.")

    finally:
        db.close()
