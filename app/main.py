from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.sessions import router as sessions_router
from app.api.scenarios import router as scenarios_router
from app.services.bootstrap_service import bootstrap_game
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(title="Detective AI Game")

# Register global exception handlers
register_exception_handlers(app)

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
