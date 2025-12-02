# System Patterns: Sala de Interrogatório

## System Architecture
- Backend-driven application using FastAPI for API endpoints.
- Layered architecture: domain (business logic), services (operations), infra (database), api (endpoints).
- Data persistence with SQLAlchemy ORM and SQLite database.
- AI integration abstracted through an adapter pattern for easy swapping (e.g., dummy to real AI).

## Key Technical Decisions
- JSON-based scenario loading for flexibility and future user-generated content.
- Session-based state management to track progress, revealed secrets, and chat history.
- Evidence confrontation triggers secret revelation, updating session state.

## Design Patterns in Use
- Repository pattern for database interactions (to be implemented in infra).
- Service layer pattern for business operations like session creation and verdict evaluation.
- Adapter pattern for AI response generation.
- Entity-relationship modeling for game elements (Scenario has Suspects, Evidences, Secrets).

## Component Relationships
- API endpoints call services, which interact with domain models and infra repositories.
- Chat service orchestrates player messages, evidence application, and NPC replies.
- Verdict service evaluates session data against scenario truths.

## Critical Implementation Paths
- Chat flow: Player message → Evidence check → State update → AI reply generation → Persistence.
- Session finalization: Accusation → Verdict calculation → Update session status.
- Scenario loading: JSON parsing → Validation → Database population.
