"""HTML card parsing functions."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from della.services.parser.models import Contact, Location, PriceInfo


def normalize_text(text: str) -> str:
    """Clean and format text by removing HTML entities."""
    return text.replace("&nbsp;", " ").strip()


def extract_final_price(text: str) -> str:
    """Extract the last price from text in format 'number грн'.

    Supports:
    - Integers: "15000 грн"
    - Decimals with comma: "84808,09 грн"
    - Numbers with spaces: "7 500 грн"
    - Numbers with NBSP: "9 000 грн"
    """
    # Regex pattern for finding prices in format: number + space + "грн"
    price_pattern = re.compile(r"(\d+(?:[\s\u00A0,]\d+)*)[\s\u00A0]*грн")

    matches = price_pattern.findall(text)

    if not matches:
        return text

    # Take the last match (last price in text)
    number_part = matches[-1]

    # Remove spaces from number (4 500 -> 4500)
    number_part = number_part.replace(" ", "").replace("\u00A0", "")

    return f"{number_part} грн"


def parse_date(card: Tag) -> str:
    """Extract the date from the card."""
    date_elem = card.select_one(".date_add")
    if date_elem:
        return normalize_text(date_elem.get_text())
    return ""


def parse_weight(card: Tag) -> Optional[str]:
    """Extract the weight from the card if exists."""
    weight_elem = card.select_one(".weight")
    if weight_elem:
        weight = normalize_text(weight_elem.get_text())
        if weight:
            return weight
    return None


def parse_volume(card: Tag) -> Optional[str]:
    """Extract the volume from the card if exists."""
    volume_elem = card.select_one(".cube")
    if volume_elem:
        volume = normalize_text(volume_elem.get_text())
        if volume:
            return volume
    return None


def parse_truck_type(card: Tag) -> str:
    """Extract the truck type from the card."""
    truck_elem = card.select_one(".truck_type")
    if truck_elem:
        return normalize_text(truck_elem.get_text())
    return ""


def parse_cargo_type(card: Tag) -> str:
    """Extract the cargo type from the card."""
    cargo_elem = card.select_one(".cargo_type")
    if cargo_elem:
        return normalize_text(cargo_elem.get_text())
    return ""


def parse_request_tags(card: Tag) -> List[str]:
    """Extract all request tags from the card."""
    tags: List[str] = []
    tag_elements = card.select(".request_text_n_tags .request_tags .tag")
    for tag_elem in tag_elements:
        tag = normalize_text(tag_elem.get_text())
        if tag:
            tags.append(tag)
    return tags


def parse_price(card: Tag) -> Optional[PriceInfo]:
    """Extract price information from the card if exists."""
    price_block = card.select_one(".request_price_block")
    if not price_block:
        return None

    # Extract main price
    main_price_elem = price_block.select_one(".price_main")
    if not main_price_elem:
        return None

    raw_text = normalize_text(main_price_elem.get_text())
    if not raw_text:
        return None

    # Extract final price from text
    main_price = extract_final_price(raw_text)

    # Extract price per km (optional)
    price_per_km: Optional[str] = None
    price_per_km_elem = price_block.select_one(".price_additional")
    if price_per_km_elem:
        per_km = normalize_text(price_per_km_elem.get_text())
        if per_km:
            price_per_km = per_km

    # Extract price tags (optional)
    price_tags: List[str] = []
    price_tag_elements = price_block.select(".price_tags .tag")
    for tag_elem in price_tag_elements:
        tag = normalize_text(tag_elem.get_text())
        if tag:
            price_tags.append(tag)

    return PriceInfo(
        main_price=main_price,
        price_per_km=price_per_km,
        price_tags=price_tags,
    )


def parse_route(card: Tag) -> Tuple[List[Location], List[Location]]:
    """Extract FROM and TO cities from the route."""
    route_elem = card.select_one(".request_route .request_distance")
    if not route_elem:
        return [], []

    # Get the HTML content to parse it properly
    html = str(route_elem)

    # Split by em-dash to separate FROM and TO
    parts = html.split("&mdash;")
    if len(parts) != 2:
        # Try unicode em-dash
        parts = html.split("\u2014")
        if len(parts) != 2:
            return [], []

    from_cities = parse_locations_from_html(parts[0])
    to_cities = parse_locations_from_html(parts[1])

    return from_cities, to_cities


def parse_locations_from_html(html_fragment: str) -> List[Location]:
    """Extract locations from HTML fragment."""
    locations: List[Location] = []

    soup = BeautifulSoup(html_fragment, "lxml")

    # Extract all locality spans
    locality_elements = soup.select(".locality")
    for locality_elem in locality_elements:
        city = normalize_text(locality_elem.get_text())
        if not city:
            continue

        # Get parent HTML to extract country code
        parent = locality_elem.parent
        if parent:
            parent_html = str(parent)
            # Extract country code using regex (e.g., "(BE)", "(DE)")
            country_match = re.search(r"\(([A-Z]{2})\)", parent_html)
            country = country_match.group(1) if country_match else ""
        else:
            country = ""

        locations.append(Location(city=city, country=country))

    return locations


def parse_contact_from_info_block(html_content: str) -> Contact:
    """Parse contact information from request_info_block HTML."""
    soup = BeautifulSoup(html_content, "lxml")

    contact = Contact()

    # Extract company name
    company_link = soup.select_one(".company_name a.company_link")
    if company_link:
        contact.company_name = normalize_text(company_link.get_text())

    # Extract contact name
    contact_name = soup.select_one(".contact_name")
    if contact_name:
        contact.name = normalize_text(contact_name.get_text())

    # Extract phones
    phone_elements = soup.select(".contact.phones .value a")
    for phone_elem in phone_elements:
        phone = normalize_text(phone_elem.get_text())
        if phone:
            contact.phone.append(phone)

    # Extract emails
    email_elements = soup.select(".contact.email .value a")
    for email_elem in email_elements:
        email = normalize_text(email_elem.get_text())
        if email:
            contact.email.append(email)

    return contact
