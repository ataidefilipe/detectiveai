# Active Context: Sala de Interrogatório

## Current Work Focus
- Implementing the backend MVP as per backlog01.md.
- Prioritizing domain models, ORM setup, scenario loading from JSON, and basic session management.
- Building towards chat functionality with dummy AI adapter.

## Recent Changes
- Project structure set up with app/ subdirectories.
- Basic FastAPI server with /health endpoint.
- Dependencies installed via requirements.txt.

## Next Steps
- Define Pydantic models for entities (T4).
- Create SQLAlchemy ORM models (T5).
- Set up database connection and initialization (T6).
- Implement JSON scenario schema and loader (T7-T9).
- Proceed to session creation and API endpoints.

## Active Decisions and Considerations
- Use dummy AI for initial testing to focus on logic without external dependencies.
- Ensure all services are testable and modular.
- Prepare for future multiplayer by designing session states generically.

## Important Patterns and Preferences
- Follow clean code principles: small functions, clear naming.
- Use Pydantic for validation to ensure data integrity.
- Structure services to handle business logic separately from API.

## Learnings and Project Insights
- Layered architecture helps in maintaining separation of concerns.
- JSON loading allows easy scenario creation without database edits.
- Early testing of verdict logic is crucial for game balance.
