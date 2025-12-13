# Services package
"""
Service layer contract (MVP):

- Services used by API controllers MUST return only
  serializable data structures (dict, list, str, int, etc).
- SQLAlchemy ORM objects must NEVER leak outside the service layer.
- Controllers should not depend on ORM behavior or session lifecycle.

This avoids DetachedInstanceError and keeps the API boundary stable.
"""
