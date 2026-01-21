"""HTTP client for fetching page content."""

import httpx

from della.services.browser.playwright_client import PlaywrightClient

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


class HTTPClient:
    """HTTP client with cookie support from browser session."""

    def __init__(self, browser_client: PlaywrightClient, base_url: str):
        """Initialize HTTP client.

        Args:
            browser_client: Playwright client with authenticated session.
            base_url: Base URL for requests.
        """
        self.base_url = base_url

        # Get cookies from browser
        cookies = browser_client.get_cookies()

        # Create httpx client with cookies
        self._client = httpx.Client(
            timeout=30.0,
            headers=DEFAULT_HEADERS,
            cookies={c["name"]: c["value"] for c in cookies},
        )

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()

    def get(self, url: str) -> bytes:
        """Fetch content from URL.

        Args:
            url: URL to fetch.

        Returns:
            Response body as bytes.

        Raises:
            httpx.HTTPError: If request fails.
        """
        response = self._client.get(url)
        response.raise_for_status()
        return response.content
