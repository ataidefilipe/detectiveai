import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.domain.schema_scenario import ScenarioConfig

with open('tests/sample_scenario.json', 'r') as f:
    data = json.load(f)

try:
    scenario = ScenarioConfig(**data)
    print("Validation successful.")
    print(scenario)
except Exception as e:
    print("Validation failed:", str(e))
