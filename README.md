# Antigravity Autonomous MVP Pipeline

This repository is **file-driven**. Agents coordinate and work by creating/updating/moving files.
You act as **Product Owner (PO)**: provide inputs and prioritize outcomes; Orchestrator routes work.

## Where you provide inputs (PO)
- Drop files into: `/work/inbox/`
- Or write raw notes into: `/state/NOTES_INBOX.md`

Agents will consume inputs and move them to processed/archive folders.

## Single Source of Truth
- Project status: `/state/STATUS.md` (owned by Orchestrator)
- Backlog board: `/backlog/BOARD.md` (owned by Docs&Backlog + QA Runner)
- Task specs: `/backlog/tasks/*.md` (updated by the agent responsible for the stage)
- Protocols: `/docs/PROTOCOLS.md` and `/docs/FLOW.md`

## MVP Principles
- Small, shippable vertical slices
- Minimal architecture
- Minimal tests but high-signal
- No heavy security engineering

## Database Schema Evolution Policy (MVP)
The MVP explicitly **does not** use Alembic or implicit migration tools to keep operations lightweight.
As such, any structural changes made to the SQLAlchemy models (e.g. adding columns, dropping variables, changing types) will cause silent failures or crashes if the outdated SQLite schema remains.

**Mandatory action:** If you change `app/infra/db_models.py`, you must flush the local database.
Run the integrated script to drop all tables and let `Base.metadata.create_all()` reinitialize them safely:
```bash
python reset_db.py --force
```
