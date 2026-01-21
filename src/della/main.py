"""Головна точка входу для програми della."""

import random
import sys
import time
from typing import Optional

from della.config import load_config
from della.errors import InvalidCredentialsError
from della.handlers import SignalHandler
from della.services.browser import PlaywrightClient
from della.services.exporter import Exporter
from della.services.http_client import HTTPClient
from della.services.parser import ParserService
from della.storage import CardStorage

POLL_INTERVAL_MIN = 120  # мінімальний інтервал
POLL_INTERVAL_MAX = 160  # максимальний інтервал


def main() -> None:
    """Головна точка входу."""
    browser_client: Optional[PlaywrightClient] = None
    http_client: Optional[HTTPClient] = None
    shutdown_requested = False

    def request_shutdown() -> None:
        nonlocal shutdown_requested
        shutdown_requested = True

    try:
        print("Запуск програми...")

        # Завантаження конфігурації
        try:
            cfg = load_config()
        except FileNotFoundError as e:
            print(f"Помилка: {e}")
            _wait_for_exit()
            return
        except Exception as e:
            print(f"Помилка конфігурації: {e}")
            _wait_for_exit()
            return

        # Ініціалізація браузерного клієнта
        browser_client = PlaywrightClient(cfg)
        browser_client.start()

        # Перевірка авторизації
        print("Авторизація...")
        try:
            browser_client.auth_if_needed()
        except InvalidCredentialsError:
            print("Помилка: Невірний логін або пароль.")
            _wait_for_exit()
            return

        print("Авторизація успішна")

        # Створення HTTP клієнта
        http_client = HTTPClient(browser_client, str(cfg.url))

        # Створення парсер-сервісу з фільтром ПДВ
        vat_filter = cfg.get_vat_filter()
        parser_service = ParserService(vat_filter)

        # Створення сховища карток
        card_storage = CardStorage()

        # Створення експортера для Excel
        card_exporter = Exporter("./exports", "cargo_export")

        # Налаштування обробника сигналів
        signal_handler = SignalHandler(card_storage, card_exporter)
        signal_handler.setup(request_shutdown)

        # Початкове завантаження
        content = http_client.get(str(cfg.url))
        first_card = parser_service.parse_first_card(content)

        last_request_id = ""

        if first_card is None:
            all_cards = parser_service.parse_cards_until_id(content, "")
            if all_cards:
                first_card = all_cards[0]
                last_request_id = first_card.request_id
                card_storage.add_card(first_card)
        else:
            last_request_id = first_card.request_id
            card_storage.add_card(first_card)

        # Запуск циклу моніторингу
        print("\n=== Моніторинг нових карток ===")
        print("Натисніть Ctrl+C для завершення...\n")

        while not shutdown_requested:
            poll_interval = random.randint(POLL_INTERVAL_MIN, POLL_INTERVAL_MAX)
            for _ in range(poll_interval):
                if shutdown_requested:
                    break
                time.sleep(1)

            if shutdown_requested:
                break

            try:
                content = http_client.get(str(cfg.url))
                new_cards = parser_service.parse_cards_until_id(content, last_request_id)
            except Exception:
                continue

            if new_cards:
                last_request_id = new_cards[0].request_id
                card_storage.add_cards(new_cards)
                print(f"+ {len(new_cards)} нових карток (всього: {card_storage.count()})")

        signal_handler.wait_for_shutdown(timeout=30)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Помилка: {e}")
        _wait_for_exit()
    finally:
        if http_client:
            http_client.close()
        if browser_client:
            try:
                browser_client.close()
            except Exception:
                pass
        sys.exit(0)


def _wait_for_exit() -> None:
    """Очікування натискання Enter для виходу."""
    print("\nНатисніть Enter для виходу...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
