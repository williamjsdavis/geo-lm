"""GemPy-specific exceptions for geo-lm."""

from geo_lm.exceptions import GeoLMError


class GemPyError(GeoLMError):
    """Base exception for GemPy operations."""

    pass


class GemPyConfigError(GemPyError):
    """Configuration errors before model creation."""

    pass


class GemPyValidationError(GemPyError):
    """Validation errors in model configuration or data."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        msg = self.args[0]
        if self.errors:
            error_list = "\n  - ".join(self.errors)
            msg += f"\n  - {error_list}"
        return msg


class GemPyBuildError(GemPyError):
    """Errors during GemPy model construction."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}

    def __str__(self) -> str:
        msg = self.args[0]
        if self.details:
            msg += f"\nDetails: {self.details}"
        return msg


class SpatialGenerationError(GemPyError):
    """Errors during spatial data generation."""

    pass


class TransformationError(GemPyError):
    """Errors during DSL to GemPy transformation."""

    pass
