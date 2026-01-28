"""Custom exceptions for Lardi-Trans API client."""

from typing import Optional


class LardiTransError(Exception):
    """Base exception for Lardi-Trans errors."""

    pass


class InvalidTokenError(LardiTransError):
    """Raised when API token is invalid or expired."""

    pass


class MissingPriceError(LardiTransError):
    """Raised when price is required but not provided."""

    pass


class MissingWeightError(LardiTransError):
    """Raised when weight is required but not provided."""

    pass


class RateLimitedError(LardiTransError):
    """Raised when API rate limit is exceeded (HTTP 429)."""

    pass


class APIError(LardiTransError):
    """Raised for general API errors."""

    def __init__(self, message: str, code: Optional[int] = None):
        """Initialize API error.

        Args:
            message: Error message from API.
            code: Optional error code.
        """
        super().__init__(message)
        self.code = code


class DuplicateProposalError(LardiTransError):
    """Raised when attempting to create a duplicate cargo proposal."""

    pass


class TownNotFoundError(LardiTransError):
    """Raised when town lookup fails."""

    def __init__(self, query: str, country_sign: str):
        """Initialize town not found error.

        Args:
            query: Search query that failed.
            country_sign: Country code used in search.
        """
        super().__init__(f"Town not found: {query} ({country_sign})")
        self.query = query
        self.country_sign = country_sign
