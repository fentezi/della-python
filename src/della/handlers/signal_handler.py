"""Обробник сигналів для graceful shutdown."""

import signal
import threading
from typing import Callable, Optional

from della.storage.card_storage import CardStorage


class SignalHandler:
    """Обробник системних сигналів для graceful shutdown."""

    def __init__(self, storage: CardStorage):
        """Ініціалізація обробника сигналів.

        Args:
            storage: Сховище карток.
        """
        self.storage = storage
        self._shutdown_event = threading.Event()
        self._cancel_callback: Optional[Callable[[], None]] = None
        self._handled = False

    def setup(self, cancel_callback: Callable[[], None]) -> None:
        """Налаштування обробників сигналів.

        Args:
            cancel_callback: Функція для виклику при завершенні.
        """
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

        self._shutdown_event.set()

        if self._cancel_callback:
            self._cancel_callback()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Очікування завершення shutdown.

        Args:
            timeout: Максимальний час очікування в секундах.

        Returns:
            True якщо shutdown завершено, False якщо timeout.
        """
        return self._shutdown_event.wait(timeout)

    @property
    def is_shutdown_requested(self) -> bool:
        """Перевірка чи запитано shutdown."""
        return self._shutdown_event.is_set()
