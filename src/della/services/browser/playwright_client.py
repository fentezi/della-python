"""Playwright browser client for authentication and cookie extraction."""

import os
import random
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from della.config import Config
from della.errors import BrowserError, InvalidCredentialsError


def install_browsers() -> None:
    """Install Playwright browsers if not present."""
    try:
        from playwright._impl._driver import compute_driver_executable
        driver_executable = compute_driver_executable()
        subprocess.run(
            [str(driver_executable), "install", "chromium"],
            check=True,
            capture_output=True,
        )
    except Exception:
        # Fallback method
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)


def sanitize_email(email: str) -> str:
    """Sanitize email for use as directory name."""
    sanitized = email.replace("@", "_at_")
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", sanitized)
    return sanitized


def human_sleep(base_ms: int) -> None:
    """Sleep for a human-like random duration.

    Args:
        base_ms: Base sleep time in milliseconds.
    """
    jitter = random.randint(-base_ms // 4, base_ms // 4)
    time.sleep((base_ms + jitter) / 1000)


class PlaywrightClient:
    """Browser client using Playwright for authentication."""

    def __init__(self, cfg: Config):
        """Initialize Playwright client.

        Args:
            cfg: Application configuration.
        """
        self.cfg = cfg
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._profile_dir: Optional[str] = None

    def _get_profile_path(self) -> Optional[str]:
        """Get profile directory path."""
        persistence = self.cfg.get_browser_persistence()

        if not persistence.enabled:
            return None

        profiles_dir = persistence.profiles_dir
        if not os.path.isabs(profiles_dir):
            profiles_dir = os.path.join(os.getcwd(), profiles_dir)

        user_dir = os.path.join(profiles_dir, sanitize_email(self.cfg.auth.email))
        return user_dir

    def _ensure_profile_dir(self) -> None:
        """Create profile directory if needed."""
        if self._profile_dir:
            os.makedirs(self._profile_dir, mode=0o700, exist_ok=True)

    def start(self) -> None:
        """Start browser and navigate to URL."""
        self._profile_dir = self._get_profile_path()
        self._ensure_profile_dir()

        self._playwright = sync_playwright().start()

        # Try to launch browser, install if not found
        try:
            self._launch_browser()
        except Exception as e:
            if "Executable doesn't exist" in str(e):
                print("Встановлення браузера (один раз)...")
                install_browsers()
                self._launch_browser()
            else:
                raise

        # Navigate to URL
        self._page.goto(str(self.cfg.url), wait_until="domcontentloaded")

    def _launch_browser(self) -> None:
        """Launch the browser."""
        if self._profile_dir:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=self._profile_dir,
                headless=True,
                user_agent=USER_AGENT,
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context(user_agent=USER_AGENT)
            self._page = self._context.new_page()

    def close(self) -> None:
        """Close browser and cleanup."""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _is_logged_in(self) -> bool:
        """Check if user is already logged in."""
        if not self._page:
            return False

        try:
            self._page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        # Check for login button - if visible, user is not logged in
        try:
            login_button = self._page.query_selector(".header__buttons_login")
            if login_button and login_button.is_visible():
                return False
        except Exception:
            pass

        # Check for cookies as additional verification
        cookies = self._context.cookies() if self._context else []
        if cookies:
            return True

        return False

    def auth_if_needed(self) -> None:
        """Авторизація якщо ще не виконана."""
        if self._is_logged_in():
            return

        try:
            self._auth()
        except InvalidCredentialsError:
            # Remove profile directory on auth failure
            if self._profile_dir and os.path.exists(self._profile_dir):
                shutil.rmtree(self._profile_dir, ignore_errors=True)
            raise

    def _auth(self) -> None:
        """Perform authentication flow."""
        if not self._page:
            raise BrowserError("Browser page not initialized")

        # Wait for page stability
        try:
            self._page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        human_sleep(500)

        # Click login button using XPath
        login_button = self._page.locator(
            "xpath=/html/body/table/tbody/tr[1]/td/table/tbody/tr[1]/td[3]/div[3]/div/div[1]"
        )
        login_button.wait_for(state="visible", timeout=10000)
        human_sleep(300)
        login_button.click()

        human_sleep(800)

        # Wait for login form
        time.sleep(2)
        human_sleep(500)

        # Find and fill login input
        login_input = self._page.locator("xpath=//*[@id='login']")
        login_input.wait_for(state="visible", timeout=15000)
        human_sleep(400)
        self._human_type_text(login_input, self.cfg.auth.email)

        human_sleep(600)

        # Find and fill password input
        pass_input = self._page.locator("xpath=//*[@id='password']")
        pass_input.wait_for(state="visible", timeout=15000)
        human_sleep(300)
        self._human_type_text(pass_input, self.cfg.auth.password)

        human_sleep(500)

        # Press Enter to submit
        self._page.keyboard.press("Enter")

        time.sleep(5)

        # Check for login error
        try:
            login_menu = self._page.locator("xpath=//*[@id='signinmwnd']/div[3]")
            if login_menu.count() > 0 and login_menu.is_visible():
                raise InvalidCredentialsError()
        except InvalidCredentialsError:
            raise
        except Exception:
            pass

        human_sleep(500)

        # Зміна налаштувань після входу (необов'язково)
        try:
            self._change_settings()
        except Exception:
            pass

    def _human_type_text(self, element, text: str) -> None:
        """Type text with human-like behavior.

        Args:
            element: Playwright locator.
            text: Text to type.
        """
        element.wait_for(state="visible", timeout=15000)
        human_sleep(300)
        element.click()
        human_sleep(300)

        # Clear existing text
        element.select_text()
        element.fill("")
        human_sleep(200)

        # Type new text
        element.fill(text)
        human_sleep(200)

    def _change_settings(self) -> None:
        """Change display settings after login."""
        if not self._page:
            return

        # Click count dropdown
        count_button = self._page.locator(
            "xpath=/html/body/table/tbody/tr[2]/td/div[1]/div[2]/div[2]/div[3]/div/div[2]"
        )
        count_button.wait_for(state="visible", timeout=5000)
        human_sleep(300)
        count_button.click()
        human_sleep(800)

        # Select last option (maximum items)
        last_count = self._page.locator(
            "xpath=/html/body/table/tbody/tr[2]/td/div[1]/div[2]/div[2]/div[3]/div/div[3]/div/ul/li[3]"
        )
        last_count.wait_for(state="visible", timeout=3000)
        last_count.click()
        human_sleep(500)

        # Click conversation dropdown
        conversation_button = self._page.locator(
            "xpath=/html/body/table/tbody/tr[2]/td/div[1]/div[2]/div[2]/div[4]/div[1]/div[2]"
        )
        conversation_button.wait_for(state="visible", timeout=5000)
        human_sleep(300)
        conversation_button.click()
        human_sleep(800)

        # Select conversation option
        conversation = self._page.locator(
            "xpath=/html/body/table/tbody/tr[2]/td/div[1]/div[2]/div[2]/div[4]/div[1]/div[3]/div/ul/li[4]"
        )
        conversation.wait_for(state="visible", timeout=3000)
        conversation.click()
        human_sleep(500)

    def get_cookies(self) -> List[Dict]:
        """Get cookies from browser.

        Returns:
            List of cookie dictionaries.
        """
        if not self._context:
            return []

        cookies = self._context.cookies()

        # Convert to httpx-compatible format
        return [
            {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            }
            for c in cookies
        ]
