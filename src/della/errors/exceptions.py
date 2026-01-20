"""Custom exceptions for della application."""


class DellaError(Exception):
    """Base exception for della application."""

    pass


class InvalidCredentialsError(DellaError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid login credentials"):
        self.message = message
        super().__init__(self.message)


class BrowserError(DellaError):
    """Raised when browser automation fails."""

    def __init__(self, message: str = "Browser automation error"):
        self.message = message
        super().__init__(self.message)


class ParsingError(DellaError):
    """Raised when HTML parsing fails."""

    def __init__(self, message: str = "HTML parsing error"):
        self.message = message
        super().__init__(self.message)


class ConfigError(DellaError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Configuration error"):
        self.message = message
        super().__init__(self.message)
