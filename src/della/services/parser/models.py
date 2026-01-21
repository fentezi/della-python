"""Data models for parsed cargo cards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Location:
    """Location with city and country code."""

    city: str
    country: str = ""


@dataclass
class PriceInfo:
    """Price information for a cargo card."""

    main_price: str
    price_per_km: Optional[str] = None
    price_tags: List[str] = field(default_factory=list)


@dataclass
class CargoCard:
    """Parsed cargo request data."""

    request_id: str
    date: str
    truck_type: str
    cargo_type: str
    weight: Optional[str] = None
    volume: Optional[str] = None
    from_cities: List[Location] = field(default_factory=list)
    to_cities: List[Location] = field(default_factory=list)
    request_tags: List[str] = field(default_factory=list)
    price: Optional[PriceInfo] = None
    url: str = ""
