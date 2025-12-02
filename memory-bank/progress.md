# Progress: Sala de Interrogatório

## What Works
- Basic project structure established (app/ with subdirs, tests/).
- Dependencies installed (FastAPI, Uvicorn, SQLAlchemy, Pydantic).
- Simple FastAPI server running with /health endpoint.

## What's Left to Build
- Define Pydantic and SQLAlchemy models (T4-T5).
- Database connection and initialization (T6).
- JSON scenario schema and loader (T7-T9).
- Session creation and management services/API (T10-T13).
- Chat services, evidence application, dummy AI (T14-T20).
- Suspect progress calculation and closing (T21-T24).
- Verdict evaluation and accusation API (T25-T27).
- Unit and integration tests (T28-T30).
- Integration of real AI adapter.
- Frontend interface (post-MVP).

## Current Status
- Project in early development phase.
- Backend setup complete, ready for model implementation.
- No functional game loop yet; focusing on domain and services.

## Known Issues
- No real AI integration; using dummy for now.
- Database not yet initialized; needs init_db implementation.
- No scenarios loaded; piloto.json to be created.

## Evolution of Project Decisions
- Started with conceptual design in README.md.
- Defined detailed backlog for MVP implementation.
- Chosen tech stack for simplicity and scalability.
- Deferred multiplayer and advanced features to focus on core mechanics.
