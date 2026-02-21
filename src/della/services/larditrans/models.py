"""Pydantic models for Lardi-Trans API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    """Location point in the cargo route."""

    country_sign: str = Field(..., alias="countrySign")
    town_id: int = Field(..., alias="townId")
    area_id: int = Field(..., alias="areaId")

    model_config = {"populate_by_name": True}


class PaymentForm(BaseModel):
    """Payment form entry in a cargo proposal request."""

    id: int
    vat: bool = Field(default=False, alias="vat")

    model_config = {"populate_by_name": True}


class CargoProposalRequest(BaseModel):
    """Request body for creating a cargo proposal."""

    date_from: str = Field(..., alias="dateFrom")
    date_to: str = Field(default="", alias="dateTo")
    payment_value: float = Field(..., alias="paymentValue")
    payment_currency_id: int = Field(..., alias="paymentCurrencyId")
    cargo_body_type_ids: List[int] = Field(..., alias="cargoBodyTypeIds")
    size_mass: float = Field(..., alias="sizeMass")
    waypoint_source: List[Waypoint] = Field(..., alias="waypointListSource")
    waypoint_target: List[Waypoint] = Field(..., alias="waypointListTarget")
    content_name: str = Field(..., alias="contentName")
    size_volume: Optional[float] = Field(default=None, alias="sizeVolume")
    size_length: Optional[float] = Field(default=None, alias="sizeLength")
    size_width: Optional[float] = Field(default=None, alias="sizeWidth")
    size_height: Optional[float] = Field(default=None, alias="sizeHeight")
    note: Optional[str] = Field(default=None, alias="note")
    contact_id: Optional[int] = Field(default=None, alias="contactId")
    payment_forms: Optional[List[PaymentForm]] = Field(default=None, alias="paymentForms")

    model_config = {"populate_by_name": True}


class CargoProposalResponse(BaseModel):
    """API response for creating a cargo proposal."""

    id: int
    error: Optional[str] = None


class APIErrorResponse(BaseModel):
    """Error response from Lardi-Trans API."""

    code: int
    message: str


class Town(BaseModel):
    """Town from the references search API."""

    id: int
    name: str
    country_sign: str = Field(..., alias="countrySign")
    area_id: int = Field(..., alias="areaId")

    model_config = {"populate_by_name": True}


class BodyType(BaseModel):
    """Body type from the references API."""

    id: int
    name: str


class Currency(BaseModel):
    """Currency from the references API."""

    id: int
    name: str


class PaymentUnit(BaseModel):
    """Payment unit from the references API."""

    id: int
    name: str


class PaymentType(BaseModel):
    """Payment type from the references API."""

    id: int
    name: str


class ContactPhone(BaseModel):
    """Phone number of a contact person."""

    number: str
    messengers: List[str] = Field(default_factory=list)


class Contact(BaseModel):
    """Contact person from the Lardi-Trans API."""

    contact_id: int = Field(..., alias="contactId")
    face: str
    phones: List[ContactPhone] = Field(default_factory=list)
    email: str = ""
    visible: bool = True

    model_config = {"populate_by_name": True}
