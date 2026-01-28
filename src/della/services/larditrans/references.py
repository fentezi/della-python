"""Thread-safe reference cache for Lardi-Trans API."""

import threading
from typing import Dict, Optional

from della.services.larditrans.models import Town


class ReferenceCache:
    """Thread-safe cache for reference data from Lardi-Trans API."""

    def __init__(self) -> None:
        """Initialize empty reference cache."""
        self._lock = threading.RLock()
        self._body_types: Dict[str, int] = {}  # normalized name -> ID
        self._currencies: Dict[str, int] = {}  # normalized name -> ID
        self._payment_types: Dict[str, int] = {}  # normalized name -> ID
        self._towns: Dict[str, Town] = {}  # "city|country" -> Town

    def set_body_types(self, body_types: Dict[str, int]) -> None:
        """Set body types mapping.

        Args:
            body_types: Mapping of normalized name to ID.
        """
        with self._lock:
            self._body_types = body_types.copy()

    def get_body_type_id(self, name: str) -> Optional[int]:
        """Get body type ID by name.

        Args:
            name: Body type name (case-insensitive).

        Returns:
            Body type ID or None if not found.
        """
        normalized = name.lower().strip()
        with self._lock:
            return self._body_types.get(normalized)

    def set_currencies(self, currencies: Dict[str, int]) -> None:
        """Set currencies mapping.

        Args:
            currencies: Mapping of normalized name to ID.
        """
        with self._lock:
            self._currencies = currencies.copy()

    def get_currency_id(self, name: str) -> Optional[int]:
        """Get currency ID by name.

        Args:
            name: Currency name (case-insensitive).

        Returns:
            Currency ID or None if not found.
        """
        normalized = name.lower().strip()
        with self._lock:
            return self._currencies.get(normalized)

    def set_payment_types(self, types: Dict[str, int]) -> None:
        """Set payment types mapping.

        Args:
            types: Mapping of normalized name to ID.
        """
        with self._lock:
            self._payment_types = types.copy()

    def get_payment_type_id(self, name: str) -> Optional[int]:
        """Get payment type ID by name.

        Args:
            name: Payment type name (case-insensitive).

        Returns:
            Payment type ID or None if not found.
        """
        normalized = name.lower().strip()
        with self._lock:
            return self._payment_types.get(normalized)

    def get_town(self, query: str, country_sign: str) -> Optional[Town]:
        """Get cached town by query and country.

        Args:
            query: City name.
            country_sign: Country ISO code.

        Returns:
            Cached Town or None if not found.
        """
        cache_key = f"{query.lower()}|{country_sign.upper()}"
        with self._lock:
            return self._towns.get(cache_key)

    def set_town(self, query: str, country_sign: str, town: Town) -> None:
        """Cache a town result.

        Args:
            query: City name used in search.
            country_sign: Country ISO code.
            town: Town object to cache.
        """
        cache_key = f"{query.lower()}|{country_sign.upper()}"
        with self._lock:
            self._towns[cache_key] = town
