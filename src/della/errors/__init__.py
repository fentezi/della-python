"""Custom exceptions module."""

from della.errors.exceptions import (
    DellaError,
    InvalidCredentialsError,
    BrowserError,
    ParsingError,
    ConfigError,
)

__all__ = [
    "DellaError",
    "InvalidCredentialsError",
    "BrowserError",
    "ParsingError",
    "ConfigError",
]
