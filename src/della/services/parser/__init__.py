"""Parser module."""

from della.services.parser.models import CargoCard, Location, PriceInfo
from della.services.parser.parser import ParserService

__all__ = ["CargoCard", "Location", "ParserService", "PriceInfo"]
