"""Parser module."""

from della.services.parser.models import Location, PriceInfo, Contact, CargoCard
from della.services.parser.parser import ParserService

__all__ = ["Location", "PriceInfo", "Contact", "CargoCard", "ParserService"]
