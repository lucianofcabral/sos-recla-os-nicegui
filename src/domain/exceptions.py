class DomainError(Exception):
    """Base exception for domain-level errors."""


class EntityNotFoundError(DomainError):
    """Raised when a repository cannot find an entity by id."""


class DuplicateEntityError(DomainError):
    """Raised when saving an entity that already exists (e.g. duplicate username)."""
