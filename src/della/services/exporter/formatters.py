"""Formatting utilities for Excel export."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from della.services.parser.models import CargoCard, Location, PriceInfo


def split_date_range(date: str) -> Tuple[str, str]:
    """Split date into start and end parts.

    Examples:
        "29.12–30.12" -> ("29.12", "30.12")
        "29.12.2024" -> ("29.12.2024", "")
        "29.12" -> ("29.12", "")

    Args:
        date: Date string, possibly a range.

    Returns:
        Tuple of (start_date, end_date).
    """
    # Check different dash types: en dash (–), em dash (—), hyphen (-)
    separators = ["–", "—", "-"]

    for sep in separators:
        if sep in date:
            parts = date.split(sep)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()

    # If no separator found, whole date is the start date
    return date, ""


def calculate_max_cities(cards: List[CargoCard]) -> Tuple[int, int]:
    """Determine maximum number of cities for 'From' and 'To' columns.

    Args:
        cards: List of cargo cards.

    Returns:
        Tuple of (max_from, max_to).
    """
    max_from = 0
    max_to = 0

    for card in cards:
        if len(card.from_cities) > max_from:
            max_from = len(card.from_cities)
        if len(card.to_cities) > max_to:
            max_to = len(card.to_cities)

    return max_from, max_to


def format_location(loc: Location) -> str:
    """Format a location as 'City (Country)'.

    Args:
        loc: Location object.

    Returns:
        Formatted string.
    """
    if loc.country:
        return f"{loc.city} ({loc.country})"
    return loc.city


def format_tags(tags: List[str]) -> str:
    """Join tags with '; ' separator.

    Args:
        tags: List of tags.

    Returns:
        Joined string.
    """
    if not tags:
        return ""
    return "; ".join(tags)


def format_price(price: Optional[PriceInfo]) -> Tuple[str, str, str]:
    """Safely extract price data.

    Args:
        price: PriceInfo object or None.

    Returns:
        Tuple of (main_price, price_per_km, price_tags).
    """
    if price is None:
        return "", "", ""

    main_price = price.main_price
    price_per_km = price.price_per_km or ""
    price_tags = format_tags(price.price_tags)

    return main_price, price_per_km, price_tags


def get_string_value(value: Optional[str]) -> str:
    """Return string value or empty string for None.

    Args:
        value: Optional string.

    Returns:
        Value or empty string.
    """
    if value is None:
        return ""
    return value


def generate_file_name(prefix: str) -> str:
    """Generate filename with timestamp.

    Args:
        prefix: Filename prefix.

    Returns:
        Filename with timestamp.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}.xlsx"


def create_headers(max_from: int, max_to: int) -> List[str]:
    """Create headers with dynamic columns for cities.

    Args:
        max_from: Maximum number of 'From' cities.
        max_to: Maximum number of 'To' cities.

    Returns:
        List of header strings.
    """
    headers = [
        "ID Заявки",
        "Дата початку",
        "Дата кінця",
        "Маса",
        "Об'єм",
        "Тип вантажівки",
        "Тип вантажу",
    ]

    # Add dynamic 'From' columns
    for i in range(1, max_from + 1):
        headers.append(f"Звідки {i}")

    # Add dynamic 'To' columns
    for i in range(1, max_to + 1):
        headers.append(f"Куди {i}")

    # Add remaining fixed columns
    headers.extend([
        "Теги запиту",
        "Основна ціна",
        "Ціна за км",
        "Теги ціни",
        "Компанія",
        "Контактна особа",
        "Телефон",
        "Email",
    ])

    return headers
