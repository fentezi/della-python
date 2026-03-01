"""Data models for parsed cargo cards."""

from __future__ import annotations

import hashlib
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
    length: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    from_cities: List[Location] = field(default_factory=list)
    to_cities: List[Location] = field(default_factory=list)
    request_tags: List[str] = field(default_factory=list)
    price: Optional[PriceInfo] = None
    url: str = ""
    is_closed: bool = False
    city_pair: str = ""

    @property
    def fingerprint(self) -> str:
        """Stable hash based on card content, independent of session.

        Uses city_pair (stable numeric IDs like "208,5404"),
        date, truck type, weight, volume, and cargo type.
        """
        content = "|".join([
            self.truck_type.strip(),
            self.cargo_type.strip(),
            self.weight or "",
            self.volume or "",
            self.city_pair,
        ])
        return hashlib.sha256(content.encode()).hexdigest()[:20]
