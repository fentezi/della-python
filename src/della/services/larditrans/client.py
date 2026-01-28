"""HTTP client for Lardi-Trans API."""

from typing import Dict, List, Optional
from urllib.parse import quote

import httpx

from della.services.larditrans.exceptions import (
    APIError,
    DuplicateProposalError,
    InvalidTokenError,
    RateLimitedError,
    TownNotFoundError,
)
from della.services.larditrans.models import (
    BodyType,
    CargoProposalRequest,
    CargoProposalResponse,
    Contact,
    Currency,
    PaymentType,
    Town,
)
from della.services.larditrans.references import ReferenceCache
from della.services.larditrans.retry import retry_on_rate_limit

DEFAULT_BASE_URL = "https://api.lardi-trans.com/v2"
DEFAULT_TIMEOUT = 30.0


class LardiTransClient:
    """HTTP client for Lardi-Trans API."""

    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL) -> None:
        """Initialize Lardi-Trans API client.

        Args:
            token: API token (should include "Bearer " prefix).
            base_url: Base URL for API requests.
        """
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._http_client = httpx.Client(timeout=DEFAULT_TIMEOUT)
        self._cache = ReferenceCache()

    def close(self) -> None:
        """Close the HTTP client."""
        self._http_client.close()

    def _headers(self) -> Dict[str, str]:
        """Get common request headers."""
        return {
            "Authorization": self._token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _check_html_response(self, content: bytes) -> None:
        """Check if response is HTML instead of JSON.

        Args:
            content: Response body bytes.

        Raises:
            APIError: If response appears to be HTML.
        """
        if content and content[0:1] == b"<":
            preview = content[:200].decode("utf-8", errors="replace")
            raise APIError(f"Unexpected HTML response: {preview}")

    def load_references(self) -> None:
        """Load and cache all reference data from API.

        Raises:
            InvalidTokenError: If API token is invalid.
            APIError: If API request fails.
        """
        self._load_body_types()
        self._load_currencies()
        self._load_payment_types()

    def _load_body_types(self) -> None:
        """Load body types reference."""
        resp = self._http_client.get(
            f"{self._base_url}/references/body/types",
            headers=self._headers(),
        )

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code != 200:
            raise APIError(f"Failed to load body types: {resp.status_code}")

        self._check_html_response(resp.content)

        body_types = [BodyType.model_validate(bt) for bt in resp.json()]
        mapping = {bt.name.lower().strip(): bt.id for bt in body_types}
        self._cache.set_body_types(mapping)

    def _load_currencies(self) -> None:
        """Load currencies reference."""
        resp = self._http_client.get(
            f"{self._base_url}/references/currencies",
            headers=self._headers(),
        )

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code != 200:
            raise APIError(f"Failed to load currencies: {resp.status_code}")

        self._check_html_response(resp.content)

        currencies = [Currency.model_validate(c) for c in resp.json()]
        mapping = {c.name.lower().strip(): c.id for c in currencies}
        self._cache.set_currencies(mapping)

    def _load_payment_types(self) -> None:
        """Load payment types reference."""
        resp = self._http_client.get(
            f"{self._base_url}/references/payment/types",
            headers=self._headers(),
        )

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code != 200:
            raise APIError(f"Failed to load payment types: {resp.status_code}")

        self._check_html_response(resp.content)

        types = [PaymentType.model_validate(t) for t in resp.json()]
        mapping = {t.name.lower().strip(): t.id for t in types}
        self._cache.set_payment_types(mapping)

    def get_body_type_id(self, name: str) -> Optional[int]:
        """Get body type ID from cache.

        Args:
            name: Body type name.

        Returns:
            Body type ID or None if not found.
        """
        return self._cache.get_body_type_id(name)

    def get_currency_id(self, name: str) -> Optional[int]:
        """Get currency ID from cache.

        Args:
            name: Currency name.

        Returns:
            Currency ID or None if not found.
        """
        return self._cache.get_currency_id(name)

    def get_payment_type_id(self, name: str) -> Optional[int]:
        """Get payment type ID from cache.

        Args:
            name: Payment type name.

        Returns:
            Payment type ID or None if not found.
        """
        return self._cache.get_payment_type_id(name)

    def search_town(self, query: str, country_sign: str) -> Town:
        """Search for a town by name and country.

        Uses cache for previously searched towns.
        Retries with exponential backoff on rate limiting.

        Args:
            query: City name to search.
            country_sign: Country ISO code.

        Returns:
            Found Town object.

        Raises:
            TownNotFoundError: If town is not found.
            RateLimitedError: If rate limit exceeded after retries.
            InvalidTokenError: If API token is invalid.
        """
        # Check cache first
        cached = self._cache.get_town(query, country_sign)
        if cached:
            return cached

        def _search() -> Town:
            return self._search_town_once(query, country_sign)

        town = retry_on_rate_limit(_search)
        self._cache.set_town(query, country_sign, town)
        return town

    def _search_town_once(self, query: str, country_sign: str) -> Town:
        """Execute single town search request.

        Args:
            query: City name to search.
            country_sign: Country ISO code.

        Returns:
            Found Town object.

        Raises:
            TownNotFoundError: If town is not found.
            RateLimitedError: If rate limited.
            InvalidTokenError: If API token is invalid.
        """
        url = (
            f"{self._base_url}/references/towns"
            f"?query={quote(query.strip())}"
            f"&countrySigns={country_sign}"
            f"&queryLimit=1"
            f"&language=uk"
        )

        resp = self._http_client.get(url, headers=self._headers())

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code == 429:
            raise RateLimitedError()
        if resp.status_code != 200:
            raise APIError(f"Town search failed: {resp.status_code}")

        self._check_html_response(resp.content)

        towns_data = resp.json()
        if not towns_data:
            raise TownNotFoundError(query, country_sign)

        return Town.model_validate(towns_data[0])

    def get_contacts(self) -> List[Contact]:
        """Fetch contact persons from API.

        Returns:
            List of Contact objects.

        Raises:
            InvalidTokenError: If API token is invalid.
            APIError: If API request fails.
        """
        resp = self._http_client.get(
            f"{self._base_url}/users/user/contacts",
            headers=self._headers(),
        )

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code != 200:
            raise APIError(f"Failed to get contacts: {resp.status_code}")

        self._check_html_response(resp.content)

        return [Contact.model_validate(c) for c in resp.json()]

    def create_cargo_proposal(self, request: CargoProposalRequest) -> int:
        """Create a new cargo proposal.

        Retries with exponential backoff on rate limiting.

        Args:
            request: Cargo proposal request data.

        Returns:
            Created proposal ID.

        Raises:
            DuplicateProposalError: If proposal already exists.
            RateLimitedError: If rate limit exceeded after retries.
            InvalidTokenError: If API token is invalid.
            APIError: If API request fails.
        """

        def _create() -> int:
            return self._create_cargo_proposal_once(request)

        return retry_on_rate_limit(_create)

    def _create_cargo_proposal_once(self, request: CargoProposalRequest) -> int:
        """Execute single cargo proposal creation request.

        Args:
            request: Cargo proposal request data.

        Returns:
            Created proposal ID.

        Raises:
            DuplicateProposalError: If proposal already exists.
            RateLimitedError: If rate limited.
            InvalidTokenError: If API token is invalid.
            APIError: If API request fails.
        """
        resp = self._http_client.post(
            f"{self._base_url}/proposals/my/add/cargo",
            headers=self._headers(),
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        if resp.status_code == 401:
            raise InvalidTokenError()
        if resp.status_code == 429:
            raise RateLimitedError()

        self._check_html_response(resp.content)

        if resp.status_code in (200, 201):
            result = CargoProposalResponse.model_validate(resp.json())
            if result.error:
                if "аналогичного содержания" in result.error:
                    raise DuplicateProposalError()
                raise APIError(result.error)
            return result.id

        try:
            error_data = resp.json()
            message = error_data.get("message", f"Status {resp.status_code}")
            if "аналогичного содержания" in message:
                raise DuplicateProposalError()
            raise APIError(message, error_data.get("code"))
        except (ValueError, KeyError):
            raise APIError(f"Request failed with status {resp.status_code}")
