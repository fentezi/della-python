"""Mapper for converting CargoCard to Lardi-Trans API request."""

import re
from datetime import date, datetime
from typing import List, Optional, Tuple

from della.services.larditrans.client import LardiTransClient
from della.services.larditrans.exceptions import MissingPriceError, MissingWeightError
from della.services.larditrans.mappings import (
    BODY_TYPE_MAPPING,
    COUNTRY_MAPPING,
    CURRENCY_MAPPING,
    DEFAULT_BODY_TYPE_ID,
    DEFAULT_CURRENCY_ID,
    PAYMENT_FORM_MAPPING,
)
from della.services.larditrans.models import (
    CargoProposalRequest,
    PaymentForm,
    Waypoint,
)
from della.services.parser.models import CargoCard, Location, PriceInfo


class Mapper:
    """Converts CargoCard to Lardi-Trans API request."""

    def __init__(self, client: LardiTransClient, contact_id: Optional[int] = None) -> None:
        """Initialize mapper.

        Args:
            client: Lardi-Trans API client for reference lookups.
            contact_id: Optional contact person ID to include in requests.
        """
        self._client = client
        self._contact_id = contact_id

    def map_cargo_card(self, card: CargoCard) -> CargoProposalRequest:
        """Convert a CargoCard to CargoProposalRequest.

        Args:
            card: Cargo card from della.ua parser.

        Returns:
            Request object ready for API submission.

        Raises:
            MissingPriceError: If price is required but missing.
            MissingWeightError: If weight is required but missing.
            TownNotFoundError: If location lookup fails.
        """
        if card.price is None or not card.price.main_price:
            raise MissingPriceError()

        date_from, date_to = self._map_date(card.date)
        weight = self._map_weight(card.weight)
        price_value, currency_id = self._map_price(card.price)
        body_type_ids = self._map_body_type(card.truck_type)
        waypoint_source = self._map_locations(card.from_cities)
        waypoint_target = self._map_locations(card.to_cities)

        volume: Optional[float] = None
        if card.volume:
            try:
                volume = _parse_numeric_value(card.volume)
            except ValueError:
                pass

        payment_forms: Optional[List[PaymentForm]] = None
        if card.price and card.price.price_tags:
            payment_forms = self._map_payment_forms(card.price.price_tags)

        return CargoProposalRequest(
            date_from=date_from,
            date_to=date_to,
            payment_value=price_value,
            payment_currency_id=currency_id,
            cargo_body_type_ids=body_type_ids,
            size_mass=weight,
            waypoint_source=waypoint_source,
            waypoint_target=waypoint_target,
            content_name=card.cargo_type,
            size_volume=volume,
            contact_id=self._contact_id,
            payment_forms=payment_forms,
        )

    def _map_date(self, date_str: str) -> Tuple[str, str]:
        """Parse date string to API format.

        Handles formats: "29.12–30.12", "29.12-30.12", "29.12"

        Args:
            date_str: Date string from cargo card.

        Returns:
            Tuple of (date_from, date_to) in yyyy-MM-dd format.
        """
        date_str = date_str.strip()
        date_str = date_str.replace("–", "-").replace("—", "-")

        now = datetime.now()
        current_year = now.year
        today = date(now.year, now.month, now.day)

        parts = date_str.split("-")

        if len(parts) >= 2:
            from_date = _parse_day_month(parts[0], current_year)
            to_date = _parse_day_month(parts[-1], current_year)

            if to_date < from_date:
                to_date = to_date.replace(year=to_date.year + 1)

            if from_date < today:
                from_date = today
            if to_date < from_date:
                to_date = from_date

            return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")

        single_date = _parse_day_month(date_str, current_year)
        if single_date < today:
            single_date = today

        return single_date.strftime("%Y-%m-%d"), ""

    def _map_weight(self, weight: Optional[str]) -> float:
        """Parse weight string to float.

        Args:
            weight: Weight string like "20 т".

        Returns:
            Weight in tons.

        Raises:
            MissingWeightError: If weight is missing or invalid.
        """
        if not weight:
            raise MissingWeightError()

        try:
            return _parse_numeric_value(weight)
        except ValueError as e:
            raise MissingWeightError() from e

    def _map_price(self, price: PriceInfo) -> Tuple[float, int]:
        """Parse price to value and currency ID.

        Args:
            price: Price info from cargo card.

        Returns:
            Tuple of (price_value, currency_id).

        Raises:
            MissingPriceError: If price is invalid.
        """
        try:
            value = _parse_numeric_value(price.main_price)
        except ValueError as e:
            raise MissingPriceError() from e

        currency_code = _extract_currency(price.main_price)
        currency_id = self._client.get_currency_id(currency_code)
        if currency_id is None:
            currency_id = DEFAULT_CURRENCY_ID

        return value, currency_id

    def _map_body_type(self, truck_type: str) -> List[int]:
        """Map truck type to Lardi-Trans body type IDs.

        Args:
            truck_type: Truck type from cargo card.

        Returns:
            List of body type IDs.
        """
        normalized = truck_type.lower().strip()

        lardi_name = BODY_TYPE_MAPPING.get(normalized)
        if lardi_name is None:
            for key, val in BODY_TYPE_MAPPING.items():
                if key in normalized:
                    lardi_name = val
                    break

        if lardi_name:
            body_id = self._client.get_body_type_id(lardi_name)
            if body_id is not None:
                return [body_id]

        tent_id = self._client.get_body_type_id("тент")
        if tent_id is not None:
            return [tent_id]

        return [DEFAULT_BODY_TYPE_ID]

    def _map_locations(self, locations: List[Location]) -> List[Waypoint]:
        """Convert locations to waypoints by resolving town IDs.

        Args:
            locations: List of Location objects from cargo card.

        Returns:
            List of Waypoint objects with resolved IDs.

        Raises:
            TownNotFoundError: If any location lookup fails.
        """
        waypoints = []
        for loc in locations:
            country_sign = _normalize_country_code(loc.country)
            town = self._client.search_town(loc.city, country_sign)
            waypoints.append(
                Waypoint(
                    country_sign=country_sign,
                    town_id=town.id,
                    area_id=town.area_id,
                )
            )
        return waypoints

    def _map_payment_forms(self, price_tags: List[str]) -> Optional[List[PaymentForm]]:
        """Map price tags to payment forms.

        Args:
            price_tags: List of price tag strings.

        Returns:
            List of PaymentForm objects or None if tags are empty/any.
        """
        if not price_tags:
            return None

        has_vat = any(tag.strip().lower() == "пдв" for tag in price_tags)

        if any(tag.strip().lower() == "будь-яка" for tag in price_tags):
            return None

        forms = []
        for tag in price_tags:
            trimmed = tag.strip()
            normalized = trimmed.lower()

            if normalized == "пдв":
                continue

            lardi_name = PAYMENT_FORM_MAPPING.get(normalized)
            if not lardi_name:
                continue

            type_id = self._client.get_payment_type_id(lardi_name)
            if type_id is None:
                continue

            forms.append(PaymentForm(id=type_id, vat=has_vat))

        return forms if forms else None


def _parse_numeric_value(s: str) -> float:
    """Extract numeric value from string.

    Args:
        s: String like "20 т", "15000 грн".

    Returns:
        Parsed float value.

    Raises:
        ValueError: If no numeric value found.
    """
    s = s.replace(" ", "").replace(",", ".")
    match = re.search(r"[\d.]+", s)
    if not match:
        raise ValueError(f"No numeric value found in: {s}")
    return float(match.group())


def _parse_day_month(s: str, year: int) -> date:
    """Parse "29.12" format to date.

    Args:
        s: Date string in "DD.MM" format.
        year: Year to use.

    Returns:
        Parsed date object.

    Raises:
        ValueError: If date format is invalid.
    """
    s = s.strip()
    parts = s.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid date format: {s}")

    day = int(parts[0])
    month = int(parts[1])
    return date(year, month, day)


def _extract_currency(price: str) -> str:
    """Extract currency code from price string.

    Args:
        price: Price string like "15000 грн".

    Returns:
        Lardi-Trans API currency name.
    """
    lower = price.lower()
    for key, code in CURRENCY_MAPPING.items():
        if key in lower:
            return code
    return "грн."


def _normalize_country_code(country: str) -> str:
    """Normalize country name to ISO 3166-1 alpha-2 code.

    Args:
        country: Country name or code.

    Returns:
        ISO country code.
    """
    upper = country.upper().strip()

    if upper in COUNTRY_MAPPING:
        return COUNTRY_MAPPING[upper]

    if len(upper) == 2:
        return upper

    return "UA"
