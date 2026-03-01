"""Parser service for HTML cargo cards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from bs4 import BeautifulSoup

from della.config import VATFilter
from della.errors import ParsingError
from della.services.parser.card_parser import (
    parse_card_url,
    parse_cargo_type,
    parse_city_pair,
    parse_date,
    parse_dimensions,
    parse_is_closed,
    parse_price,
    parse_request_tags,
    parse_route,
    parse_truck_type,
    parse_volume,
    parse_weight,
)
from della.services.parser.models import CargoCard


@dataclass
class PageParseResult:
    """Result of parsing one page for new and closed cards."""

    new_cards: List[CargoCard] = field(default_factory=list)
    closed_card_ids: List[str] = field(default_factory=list)
    marker_found: bool = False
    first_card_id: Optional[str] = None
    last_card_id: Optional[str] = None
    total_cards: int = 0
    filtered_by_vat: int = 0



class ParserService:
    """Service for parsing HTML cargo cards with VAT filtering."""

    def __init__(self, vat_filter: VATFilter = VATFilter.ALL):
        """Initialize parser service.

        Args:
            vat_filter: VAT filter setting (with_vat, without_vat, or all).
        """
        self.vat_filter = vat_filter

    def parse_first_card(self, html_content: bytes) -> Optional[CargoCard]:
        """Parse the first cargo card from HTML content.

        Args:
            html_content: Raw HTML bytes.

        Returns:
            Parsed CargoCard or None if filtered out.

        Raises:
            ParsingError: If no cargo cards found.
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Find first request card
        card = soup.select_one(".request_card")
        if not card:
            raise ParsingError("No cargo cards found in HTML")

        parsed_card = self._parse_card(card)
        if parsed_card is None:
            raise ParsingError("Failed to parse cargo card")

        # Apply VAT filter
        if not self._should_include_card(parsed_card):
            return None

        return parsed_card

    def parse_cards_until_id(
        self, html_content: bytes, stop_at_request_id: str
    ) -> List[CargoCard]:
        """Parse all cargo cards until encountering the specified request ID.

        Args:
            html_content: Raw HTML bytes.
            stop_at_request_id: Stop parsing when this ID is encountered.

        Returns:
            List of new cargo cards that pass the VAT filter.
        """
        soup = BeautifulSoup(html_content, "lxml")

        cards: List[CargoCard] = []
        filtered_count = 0

        # Find all request cards
        card_elements = soup.select(".request_card")

        for card_elem in card_elements:
            # Extract request ID from attribute
            request_id = card_elem.get("data-request_id")
            if not request_id:
                continue

            # Stop if we reached the previous request ID
            if request_id == stop_at_request_id:
                break

            # Parse the card
            cargo_card = self._parse_card(card_elem)
            if cargo_card is None:
                continue

            # Apply VAT filter
            if not self._should_include_card(cargo_card):
                filtered_count += 1
                continue

            cards.append(cargo_card)

        return cards

    def _parse_card(self, card) -> Optional[CargoCard]:
        """Extract all fields from a single card selection.

        Args:
            card: BeautifulSoup Tag element.

        Returns:
            Parsed CargoCard or None if parsing fails.
        """
        # Extract request ID from attribute
        request_id = card.get("data-request_id")
        if not request_id:
            return None

        # Use helper functions to extract all fields
        date = parse_date(card)
        weight = parse_weight(card)
        volume = parse_volume(card)
        length, width, height = parse_dimensions(card)
        truck_type = parse_truck_type(card)
        cargo_type = parse_cargo_type(card)
        request_tags = parse_request_tags(card)
        price = parse_price(card)
        from_cities, to_cities = parse_route(card)
        url = parse_card_url(card)
        is_closed = parse_is_closed(card)
        city_pair = parse_city_pair(card)

        return CargoCard(
            request_id=request_id,
            date=date,
            weight=weight,
            volume=volume,
            length=length,
            width=width,
            height=height,
            truck_type=truck_type,
            cargo_type=cargo_type,
            from_cities=from_cities,
            to_cities=to_cities,
            request_tags=request_tags,
            price=price,
            url=url,
            is_closed=is_closed,
            city_pair=city_pair,
        )

    def parse_page_cards(
        self, html_content: bytes, stop_at_id: str
    ) -> PageParseResult:
        """Parse one page, collecting new cards and closed card IDs.

        Iterates all .request_card elements in page order (newest first).
        Stops collecting new cards once stop_at_id is found (the marker),
        but continues scanning remaining elements for closed card IDs.

        Args:
            html_content: Raw HTML bytes for one page.
            stop_at_id: The request_id of the last known card (checkpoint).
                        Pass "" on first run to collect all cards.

        Returns:
            PageParseResult with new_cards, closed_card_ids,
            marker_found flag, first_card_id, and last_card_id.
        """
        soup = BeautifulSoup(html_content, "lxml")
        result = PageParseResult()

        card_elements = soup.select(".request_card")
        past_marker = False

        for card_elem in card_elements:
            if not card_elem.get("data-request_id"):
                continue

            cargo_card = self._parse_card(card_elem)
            if cargo_card is None:
                continue

            fp = cargo_card.fingerprint
            result.total_cards += 1

            if result.total_cards <= 3 and stop_at_id:
                print(f"[debug]   card#{result.total_cards} fp={fp} city_pair={cargo_card.city_pair} date={cargo_card.date!r} url={cargo_card.url}")

            if result.first_card_id is None:
                result.first_card_id = fp

            result.last_card_id = fp

            if fp == stop_at_id:
                result.marker_found = True
                past_marker = True
                if cargo_card.is_closed:
                    result.closed_card_ids.append(fp)
                continue

            if cargo_card.is_closed:
                result.closed_card_ids.append(fp)

            if not past_marker:
                if self._should_include_card(cargo_card):
                    result.new_cards.append(cargo_card)
                else:
                    result.filtered_by_vat += 1

        return result

    def collect_closed_ids(self, html_content: bytes) -> List[str]:
        """Scan a page and return fingerprints of all closed cards.

        Used to detect closed cards on pages beyond the marker,
        without collecting any new cards.

        Args:
            html_content: Raw HTML bytes for one page.

        Returns:
            List of fingerprints of closed cards found on the page.
        """
        soup = BeautifulSoup(html_content, "lxml")
        closed: List[str] = []
        for card_elem in soup.select(".request_card"):
            if not card_elem.get("data-request_id"):
                continue
            cargo_card = self._parse_card(card_elem)
            if cargo_card is not None and cargo_card.is_closed:
                closed.append(cargo_card.fingerprint)
        return closed

    def parse_next_page_url(
        self, html_content: bytes, next_page_num: int
    ) -> Optional[str]:
        """Find the URL for a specific page number from pagination links.

        Looks for: <a class="pages" title="перейти до стор. N">

        Args:
            html_content: Raw HTML bytes of the current page.
            next_page_num: The page number to find the link for.

        Returns:
            Full URL "https://della.ua/..." or None if not found.
        """
        soup = BeautifulSoup(html_content, "lxml")
        title_text = f"перейти до стор. {next_page_num}"

        for link in soup.select("a.pages"):
            if link.get("title", "") == title_text:
                href = link.get("href", "")
                if href:
                    return f"https://della.ua{href}"

        return None

    def _should_include_card(self, card: CargoCard) -> bool:
        """Determine if a card should be included based on VAT filter settings.

        Args:
            card: Parsed cargo card.

        Returns:
            True if the card matches the filter criteria.
        """
        # If filter is "all", include all cards
        if self.vat_filter == VATFilter.ALL:
            return True

        # If card has no price information, decide based on filter type
        if card.price is None:
            return self.vat_filter == VATFilter.WITHOUT_VAT

        # Check if card has VAT (з ПДВ) or without VAT (Без ПДВ)
        has_vat = False
        for tag in card.price.price_tags:
            tag_lower = tag.lower()
            if "без пдв" in tag_lower:
                has_vat = False
                break
            elif "пдв" in tag_lower or "з пдв" in tag_lower:
                has_vat = True
                break

        # Apply filter logic
        if self.vat_filter == VATFilter.WITH_VAT:
            return has_vat
        elif self.vat_filter == VATFilter.WITHOUT_VAT:
            return not has_vat

        return True
