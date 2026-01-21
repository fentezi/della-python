"""Parser service for HTML cargo cards."""

from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from della.config import VATFilter
from della.errors import ParsingError
from della.services.parser.card_parser import (
    parse_card_url,
    parse_cargo_type,
    parse_date,
    parse_price,
    parse_request_tags,
    parse_route,
    parse_truck_type,
    parse_volume,
    parse_weight,
)
from della.services.parser.models import CargoCard



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
        truck_type = parse_truck_type(card)
        cargo_type = parse_cargo_type(card)
        request_tags = parse_request_tags(card)
        price = parse_price(card)
        from_cities, to_cities = parse_route(card)
        url = parse_card_url(card)

        return CargoCard(
            request_id=request_id,
            date=date,
            weight=weight,
            volume=volume,
            truck_type=truck_type,
            cargo_type=cargo_type,
            from_cities=from_cities,
            to_cities=to_cities,
            request_tags=request_tags,
            price=price,
            url=url,
        )

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

        # Check if "ПДВ" exists in price tags
        has_vat = False
        for tag in card.price.price_tags:
            # Check for VAT tag (may include newline from HTML)
            if "ПДВ" in tag:
                has_vat = True
                break

        # Apply filter logic
        if self.vat_filter == VATFilter.WITH_VAT:
            return has_vat
        elif self.vat_filter == VATFilter.WITHOUT_VAT:
            return not has_vat

        return True
