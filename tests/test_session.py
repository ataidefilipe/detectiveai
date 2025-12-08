from app.services.session_service import create_session
from app.services.scenario_loader import load_scenario_from_json

# load scenario only once
scenario = load_scenario_from_json("scenarios/piloto.json")

session = create_session(scenario.id)

print("Session ID:", session.id)