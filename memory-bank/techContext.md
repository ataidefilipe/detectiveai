# Tech Context: Sala de Interrogatório

## Technologies Used
- Programming Language: Python 3.x
- Web Framework: FastAPI for API development
- ORM: SQLAlchemy for database interactions
- Database: SQLite for local persistence
- Validation: Pydantic for data models and validation
- Server: Uvicorn for running the FastAPI application
- Other: JSON for scenario configurations

## Development Setup
- Project Structure: 
  - app/: Core application code
    - api/: API endpoints
    - domain/: Business logic and models
    - infra/: Database and infrastructure
    - services/: Business services
  - tests/: Unit and integration tests
  - scenarios/: JSON files for game scenarios (to be added)
- Environment: Visual Studio Code as IDE, with Git for version control
- Database Initialization: Use SQLAlchemy to create tables via init_db function
- Running: `uvicorn app.main:app --reload`

## Technical Constraints
- MVP focused on backend logic; no frontend in initial setup
- Single-player; multiplayer features deferred
- AI is dummy implementation initially; real AI integration planned
- Local SQLite database; scalable to PostgreSQL later

## Dependencies
- fastapi
- uvicorn
- sqlalchemy
- pydantic
- (Optional) alembic for migrations

## Tool Usage Patterns
- Use FastAPI routes for all interactions (e.g., /sessions, /messages)
- Pydantic for input validation in API and JSON loading
- SQLAlchemy sessions for database transactions
- Git for version control, with remote on GitHub
