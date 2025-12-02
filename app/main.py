"""Main entry point for the detective AI game app."""

from fastapi import FastAPI

app = FastAPI(title="Detective AI Game")

@app.get("/health")
async def health():
    return {"status": "ok"}

def start_app():
    print("FastAPI app instance created.")
