from app.services.scenario_loader import load_scenario_from_json

scenario = load_scenario_from_json("scenarios/piloto.json")
print("Loaded:", scenario.id, scenario.title)