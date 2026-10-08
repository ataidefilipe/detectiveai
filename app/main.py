from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.sessions import router as sessions_router
from app.api.scenarios import router as scenarios_router
from app.services.bootstrap_service import bootstrap_game
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(title="Detective AI Game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
register_exception_handlers(app)

# -----------------------------
# Startup bootstrap (MVP)
# -----------------------------
@app.on_event("startup")
def startup_event():
    bootstrap_game()

import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Register routes
app.include_router(sessions_router)
app.include_router(scenarios_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"status": "ok", "message": "Detective AI backend running"}
