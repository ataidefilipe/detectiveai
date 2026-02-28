class DomainError(Exception):
    """Base exception for all domain-related errors."""
    pass


class NotFoundError(DomainError):
    """Raised when a resource (session, suspect, evidence) is not found."""
    pass


class RuleViolationError(DomainError):
    """Raised when a game rule is violated (e.g. invalid action, session finished)."""
    pass
