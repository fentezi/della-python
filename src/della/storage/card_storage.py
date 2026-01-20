"""Thread-safe storage for cargo cards."""

import threading
from typing import List

from della.services.parser.models import CargoCard


class CardStorage:
    """Thread-safe storage for accumulating cargo cards in memory."""

    def __init__(self):
        """Initialize empty storage."""
        self._lock = threading.RLock()
        self._cards: List[CargoCard] = []

    def add_card(self, card: CargoCard) -> None:
        """Add a single card to storage.

        Args:
            card: Cargo card to add.
        """
        with self._lock:
            self._cards.append(card)

    def add_cards(self, cards: List[CargoCard]) -> None:
        """Add multiple cards to storage.

        Args:
            cards: List of cargo cards to add.
        """
        with self._lock:
            self._cards.extend(cards)

    def get_all(self) -> List[CargoCard]:
        """Get all cards from storage.

        Returns:
            Copy of all cards for safe access.
        """
        with self._lock:
            return list(self._cards)

    def count(self) -> int:
        """Get number of cards in storage.

        Returns:
            Count of stored cards.
        """
        with self._lock:
            return len(self._cards)
