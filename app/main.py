"""Main entry point for the detective AI game app."""

from fastapi import FastAPI
from app.api.sessions import router as sessions_router

app = FastAPI(title="Detective AI Game")

# Register routes
app.include_router(sessions_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

def start_app():
    print("FastAPI app instance created.")
