"""Configuration module using Pydantic."""

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, HttpUrl


class VATFilter(str, Enum):
    """VAT filter options."""

    WITH_VAT = "with_vat"
    WITHOUT_VAT = "without_vat"
    ALL = "all"


class Auth(BaseModel):
    """Authentication configuration."""

    email: str = Field(..., description="User email")
    password: str = Field(..., alias="pass", description="User password")

    model_config = {"populate_by_name": True}


class BrowserPersistence(BaseModel):
    """Browser persistence configuration."""

    enabled: bool = True
    profiles_dir: str = "./browser-profiles"


class LardiTransConfig(BaseModel):
    """Lardi-Trans API configuration."""

    enabled: bool = False
    token: str = Field(default="", description="API token (include 'Bearer ' prefix)")
    base_url: str = Field(
        default="https://api.lardi-trans.com/v2",
        description="Base URL for API requests",
    )
    contact_id: Optional[int] = Field(
        default=None,
        description="Contact person ID for cargo proposals",
    )
    publish_delay: float = Field(
        default=1.0,
        description="Delay between publications in seconds",
    )


class Config(BaseModel):
    """Main application configuration."""

    url: HttpUrl = Field(..., description="Target URL")
    auth: Auth = Field(..., description="Authentication credentials")
    vat_filter: VATFilter = Field(
        default=VATFilter.ALL,
        description="VAT filter: with_vat, without_vat, or all",
    )
    browser_persistence: Optional[BrowserPersistence] = None
    lardi_trans: Optional[LardiTransConfig] = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is valid."""
        return str(v)

    def get_browser_persistence(self) -> BrowserPersistence:
        """Get browser persistence settings with defaults."""
        if self.browser_persistence is None:
            return BrowserPersistence()
        return self.browser_persistence

    def get_vat_filter(self) -> VATFilter:
        """Get VAT filter setting."""
        return self.vat_filter

    def get_lardi_trans(self) -> Optional[LardiTransConfig]:
        """Get Lardi-Trans configuration if enabled.

        Returns:
            LardiTransConfig if enabled and token provided, None otherwise.
        """
        if self.lardi_trans is None:
            return None
        if not self.lardi_trans.enabled:
            return None
        if not self.lardi_trans.token:
            return None
        return self.lardi_trans


def load_config(config_path: str = "./config.yaml") -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Loaded Config object.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config validation fails.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Файл конфігурації {config_path} не знайдено. "
            "Створіть config.yaml в кореневій директорії проекту."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    if raw_config is None:
        raise ValueError("Файл конфігурації порожній.")

    return Config.model_validate(raw_config)
