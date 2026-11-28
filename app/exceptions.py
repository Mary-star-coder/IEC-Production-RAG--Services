
class ServiceUnavailableError(Exception):
    """Raised when a required external service is unavailable."""


class RateLimitExceededError(ServiceUnavailableError):
    """Raised when an upstream service asks the caller to slow down."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
