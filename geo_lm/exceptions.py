"""Custom exceptions for geo-lm."""


class GeoLMError(Exception):
    """Base exception for geo-lm."""

    pass


class ConfigurationError(GeoLMError):
    """Configuration-related errors."""

    pass


class DatabaseError(GeoLMError):
    """Database operation errors."""

    pass


class NotFoundError(DatabaseError):
    """Resource not found."""

    pass


class ValidationError(GeoLMError):
    """Validation errors."""

    pass


class LLMError(GeoLMError):
    """LLM-related errors."""

    pass


class DSLParseError(GeoLMError):
    """DSL parsing errors."""

    pass


class DSLValidationError(GeoLMError):
    """DSL semantic validation errors."""

    pass
