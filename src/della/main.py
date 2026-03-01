"""Головна точка входу для програми della."""

import queue
import random
import sys
import threading
import time
from typing import Callable, List, Optional

from della.config import load_config
from della.config.config import LardiTransConfig
from della.errors import InvalidCredentialsError
from della.handlers import SignalHandler
from della.services.browser import PlaywrightClient
from della.services.http_client import HTTPClient
from della.services.larditrans import (
    Contact,
    DuplicateProposalError,
    InvalidTokenError,
    LardiTransClient,
    Mapper,
    MissingWeightError,
    TownNotFoundError,
)
from della.services.parser import ParserService
from della.services.parser.models import CargoCard
from della.storage import AppState, CardStorage

POLL_INTERVAL_MIN = 120  # мінімальний інтервал
POLL_INTERVAL_MAX = 160  # максимальний інтервал
CLOSED_SCAN_EXTRA_PAGES = 15  # скільки сторінок сканувати після маркера (тільки закриті)


class LardiTransPublisher:
    """Background publisher for Lardi-Trans API."""

    def __init__(
        self,
        config: LardiTransConfig,
        on_published: Optional[Callable[[str, int], None]] = None,
    ) -> None:
        """Initialize publisher.

        Args:
            config: Lardi-Trans configuration.
            on_published: Callback invoked with (della_id, lardi_id) after
                          each successful publication.
        """
        self._config = config
        self._on_published = on_published
        self._queue: queue.Queue[CargoCard] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[LardiTransClient] = None
        self._mapper: Optional[Mapper] = None
        self._published_count = 0
        self._pending_count = 0
        self._batch_done = threading.Event()
        self._total_published = 0

    def start(self) -> bool:
        """Start the publisher background thread.

        Returns:
            True if started successfully, False on error.
        """
        try:
            self._client = LardiTransClient(
                token=self._config.token,
                base_url=self._config.base_url,
            )
            self._client.load_references()
            self._mapper = Mapper(self._client, self._config.contact_id)

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True
        except InvalidTokenError:
            print("Lardi-Trans: невірний токен API")
            return False
        except Exception as e:
            print(f"Lardi-Trans: помилка ініціалізації: {e}")
            return False

    def stop(self) -> None:
        """Stop the publisher and wait for thread to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if self._client:
            self._client.close()

    def publish(self, cards: List[CargoCard]) -> None:
        """Queue cards for publication.

        Args:
            cards: List of cargo cards to publish.
        """
        for card in cards:
            self._queue.put(card)

    def publish_and_wait(self, cards: List[CargoCard], timeout: float = 120.0) -> int:
        """Publish cards and wait for batch completion.

        Args:
            cards: List of cargo cards to publish.
            timeout: Max time to wait for batch completion.

        Returns:
            Number of successfully published cards.
        """
        if not cards:
            return 0

        self._batch_done.clear()
        self._pending_count = len(cards)
        self._published_count = 0

        for card in cards:
            self._queue.put(card)

        self._batch_done.wait(timeout=timeout)
        return self._published_count

    def delete_proposal(self, lardi_id: int) -> None:
        """Delete a proposal from Lardi-Trans (synchronous, main-thread call).

        Args:
            lardi_id: Lardi-Trans proposal ID to delete.
        """
        if self._client is None:
            return
        self._client.throw_proposals([lardi_id])

    @property
    def total_published(self) -> int:
        """Total number of published cards."""
        return self._total_published

    def _run(self) -> None:
        """Background thread main loop."""
        while not self._stop_event.is_set():
            try:
                card = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self._publish_card(card)
            time.sleep(self._config.publish_delay)

    def _publish_card(self, card: CargoCard) -> None:
        """Publish a single card to Lardi-Trans.

        Args:
            card: Cargo card to publish.
        """
        if self._mapper is None or self._client is None:
            self._finish_card()
            return

        try:
            request = self._mapper.map_cargo_card(card)
            proposal_id = self._client.create_cargo_proposal(request)
            self._published_count += 1
            self._total_published += 1
            print(f"+ 1 в Lardi (всього: {self._total_published})")
            if self._on_published is not None:
                try:
                    self._on_published(card.fingerprint, proposal_id)
                except Exception:
                    pass
        except MissingWeightError:
            print("- пропущено: немає ваги")
        except TownNotFoundError as e:
            print(f"- пропущено: місто не знайдено ({e})")
        except DuplicateProposalError:
            print("- пропущено: дублікат")
        except InvalidTokenError:
            print("- помилка: невірний токен Lardi")
            self._stop_event.set()
        except Exception as e:
            print(f"- помилка публікації: {type(e).__name__}: {e}")
        finally:
            self._finish_card()

    def _finish_card(self) -> None:
        """Mark card as processed and signal if batch is done."""
        self._pending_count -= 1
        if self._pending_count <= 0:
            self._batch_done.set()


def main() -> None:
    """Головна точка входу."""
    browser_client: Optional[PlaywrightClient] = None
    http_client: Optional[HTTPClient] = None
    lardi_publisher: Optional[LardiTransPublisher] = None

    app_state = AppState()
    app_state.load()

    def request_shutdown() -> None:
        if lardi_publisher:
            lardi_publisher.stop()

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

        # Ініціалізація Lardi-Trans публікатора (якщо налаштовано)
        lardi_config = cfg.get_lardi_trans()
        if lardi_config:
            print("Ініціалізація Lardi-Trans...")

            # Вибір контакту
            try:
                temp_client = LardiTransClient(
                    token=lardi_config.token,
                    base_url=lardi_config.base_url,
                )
                contacts = temp_client.get_contacts()
                temp_client.close()

                if contacts:
                    selected_id = _select_contact(contacts)
                    if selected_id:
                        lardi_config.contact_id = selected_id
                        print(f"Обрано контакт ID: {selected_id}")
            except InvalidTokenError:
                print("Lardi-Trans: невірний токен API")
                lardi_config = None
            except Exception as e:
                print(f"Lardi-Trans: помилка отримання контактів: {e}")

            if lardi_config:
                lardi_publisher = LardiTransPublisher(
                    lardi_config,
                    on_published=app_state.add_proposal,
                )
                if lardi_publisher.start():
                    print("Lardi-Trans: готовий до публікації")
                else:
                    lardi_publisher = None

        # Налаштування обробника сигналів
        signal_handler = SignalHandler(card_storage)
        signal_handler.setup(request_shutdown)

        # При кожному запуску: взяти поточну першу картку як checkpoint
        # Нові картки не публікуємо — тільки відстежуємо закриті через proposal_map
        print("Оновлення контрольної точки...")
        content = http_client.get(str(cfg.url))
        first_result = parser_service.parse_page_cards(content, "")
        checkpoint = first_result.first_card_id
        if checkpoint:
            app_state.last_request_id = checkpoint
            app_state.save()
            print(f"Контрольна точка: {checkpoint}")

        # Запуск циклу моніторингу
        print("\n=== Моніторинг нових карток ===")
        print("Натисніть Ctrl+C для завершення...\n")

        while not signal_handler.is_shutdown_requested:
            poll_interval = random.randint(POLL_INTERVAL_MIN, POLL_INTERVAL_MAX)
            if signal_handler.wait_for_shutdown(timeout=poll_interval):
                break

            try:
                all_new_cards: List[CargoCard] = []
                all_closed_ids: List[str] = []
                current_url = str(cfg.url)
                page_num = 0
                marker_found = False
                closed_only_pages = 0
                last_page_result = None

                checkpoint = app_state.last_request_id
                print(f"[debug] шукаємо маркер: {checkpoint[:40]}...")

                while True:
                    page_num += 1
                    try:
                        content = http_client.get(current_url)
                    except Exception:
                        break

                    if not marker_found:
                        page_result = parser_service.parse_page_cards(
                            content, checkpoint
                        )
                        last_page_result = page_result
                        all_new_cards.extend(page_result.new_cards)
                        all_closed_ids.extend(page_result.closed_card_ids)

                        first_id = page_result.first_card_id or "none"
                        last_id = page_result.last_card_id or "none"
                        print(
                            f"[debug] стор.{page_num}: "
                            f"карток={page_result.total_cards}, "
                            f"нових={len(page_result.new_cards)}, "
                            f"VAT-фільтр={page_result.filtered_by_vat}, "
                            f"закритих={len(page_result.closed_card_ids)}, "
                            f"маркер={'ТАК' if page_result.marker_found else 'ні'}"
                        )
                        print(f"[debug]   перша: {first_id[:40]}...")
                        print(f"[debug]   остання: {last_id[:40]}...")

                        if page_result.marker_found:
                            print(f"[debug] маркер знайдено на сторінці {page_num}")
                            marker_found = True
                            if app_state.proposal_count == 0:
                                break
                    else:
                        extra_closed = parser_service.collect_closed_ids(content)
                        all_closed_ids.extend(extra_closed)
                        closed_only_pages += 1
                        if extra_closed:
                            print(f"[debug] closed-scan стор.{page_num}: закритих={len(extra_closed)}")
                        if closed_only_pages >= CLOSED_SCAN_EXTRA_PAGES:
                            break

                    next_url = parser_service.parse_next_page_url(
                        content, page_num + 1
                    )

                    if next_url is None:
                        if not marker_found and last_page_result is not None:
                            print(
                                f"[debug] маркер НЕ знайдено після {page_num} стор., "
                                f"всього нових: {len(all_new_cards)}"
                            )
                            if last_page_result.last_card_id:
                                app_state.last_request_id = last_page_result.last_card_id
                                print(f"[debug] новий checkpoint: {last_page_result.last_card_id[:40]}...")
                        break

                    current_url = next_url

                # Оновлення контрольної точки до найновішої нової картки
                if all_new_cards:
                    app_state.last_request_id = all_new_cards[0].fingerprint
                    print(f"[debug] checkpoint → {all_new_cards[0].fingerprint}")

                app_state.save()

                # Видалення закритих карток з Lardi-Trans
                if all_closed_ids:
                    print(f"[debug] закритих карток на сторінках: {len(all_closed_ids)}")
                for della_id in all_closed_ids:
                    lardi_id = app_state.get_lardi_id(della_id)
                    if lardi_id is not None and lardi_publisher is not None:
                        try:
                            lardi_publisher.delete_proposal(lardi_id)
                            app_state.remove_proposal(della_id)
                            app_state.save()
                            print(f"Видалено з Lardi: картка {della_id[:40]}...")
                        except InvalidTokenError:
                            print("Lardi-Trans: невірний токен при видаленні")
                        except Exception as e:
                            print(f"Lardi-Trans: помилка видалення {della_id[:40]}: {e}")
                        if lardi_config:
                            time.sleep(lardi_config.publish_delay)

                # Публікація нових карток
                if all_new_cards:
                    print(f"[debug] публікуємо {len(all_new_cards)} нових карток")
                    card_storage.add_cards(all_new_cards)
                    if lardi_publisher:
                        lardi_publisher.publish(all_new_cards)

            except Exception:
                continue

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Помилка: {e}")
        _wait_for_exit()
    finally:
        if lardi_publisher:
            lardi_publisher.stop()
        if http_client:
            http_client.close()
        if browser_client:
            close_thread = threading.Thread(target=browser_client.close)
            close_thread.start()
            close_thread.join(timeout=3.0)
        sys.exit(0)


def _wait_for_exit() -> None:
    """Очікування натискання Enter для виходу."""
    print("\nНатисніть Enter для виходу...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def _select_contact(contacts: List[Contact]) -> Optional[int]:
    """Вибір контакту зі списку.

    Args:
        contacts: Список контактів.

    Returns:
        ID обраного контакту або None.
    """
    if not contacts:
        return None

    print("\nОберіть контакт:")
    for i, contact in enumerate(contacts, 1):
        print(f"  {i}. {contact.face}")

    try:
        choice = input("\nНомер контакту: ").strip()
        if not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(contacts):
            return contacts[idx].contact_id
        print("Невірний номер")
        return None
    except (ValueError, EOFError, KeyboardInterrupt):
        return None


if __name__ == "__main__":
    main()
