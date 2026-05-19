"""Read-only Polymarket adapter exceptions."""


class PolymarketReadOnlyError(Exception):
    """Base exception for the read-only Polymarket adapter."""


class PolymarketHTTPError(PolymarketReadOnlyError):
    """Raised when the server returns a non-2xx response."""

    def __init__(self, status: int, url: str, body: str = "") -> None:
        self.status = status
        self.url = url
        self.body = body
        super().__init__(f"HTTP {status} from {url}")


class PolymarketResponseError(PolymarketReadOnlyError):
    """Raised when the response body cannot be parsed as expected JSON."""


class PolymarketEndpointNotVerifiedError(PolymarketReadOnlyError):
    """Raised when an endpoint is called that has not been confirmed in production.

    The adapter may still attempt the call, but callers should treat the result
    as provisional. This error is raised only when the endpoint is explicitly
    marked as unverified and the caller has not opted in to unverified calls.
    """
