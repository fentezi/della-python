"""Обробник сигналів для graceful shutdown."""

import signal
import sys
import threading
from typing import Callable, Optional

from della.services.exporter.exporter import Exporter
from della.storage.card_storage import CardStorage


class SignalHandler:
    """Обробник системних сигналів для graceful shutdown."""

    def __init__(self, storage: CardStorage, exporter: Exporter):
        """Ініціалізація обробника сигналів."""
        self.storage = storage
        self.exporter = exporter
        self._shutdown_event = threading.Event()
        self._cancel_callback: Optional[Callable[[], None]] = None
        self._handled = False

    def setup(self, cancel_callback: Callable[[], None]) -> None:
        """Налаштування обробників сигналів."""
        self._cancel_callback = cancel_callback
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame) -> None:
        """Обробка отриманого сигналу."""
        # Ігнорувати повторні сигнали
        if self._handled:
            return
        self._handled = True

        # Відключити обробник щоб уникнути повторних викликів
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        print("\n\nЗавершення...")

        if self._cancel_callback:
            self._cancel_callback()

        cards = self.storage.get_all()

        if not cards:
            print("Немає карток для експорту.")
        else:
            try:
                filepath = self.exporter.export_to_excel(cards)
                print(f"✓ Експортовано {len(cards)} карток: {filepath}")
            except Exception as e:
                print(f"Помилка експорту: {e}")

        self._shutdown_event.set()
        sys.exit(0)

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Очікування завершення shutdown."""
        return self._shutdown_event.wait(timeout)

    @property
    def is_shutdown_requested(self) -> bool:
        """Перевірка чи запитано shutdown."""
        return self._shutdown_event.is_set()
