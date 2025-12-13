from fastapi import FastAPI
from app.api.sessions import router as sessions_router
from app.api.scenarios import router as scenarios_router
from app.services.bootstrap_service import bootstrap_game

app = FastAPI(title="Detective AI Game")

# -----------------------------
# Startup bootstrap (MVP)
# -----------------------------
@app.on_event("startup")
def startup_event():
    bootstrap_game()

# Register routes
app.include_router(sessions_router)
app.include_router(scenarios_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
