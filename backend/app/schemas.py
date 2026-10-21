from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import AccountStatus, BookingStatus, EventStatus, UserRole


class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    password_confirmation: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    country: str
    tax_id: str
    requested_role: UserRole = UserRole.PARTICIPANT

    @field_validator("password_confirmation")
    @classmethod
    def passwords_match(cls, value: str, info):
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("password_confirmation must match password")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    status: AccountStatus


class UserAdminResponse(UserResponse):
    phone: str
    address: str
    city: str
    country: str
    tax_id: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TicketTypeCreate(BaseModel):
    name: str
    price: Annotated[Decimal, Field(ge=0)]
    quantity: Annotated[int, Field(gt=0)]


class EventCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    categories: Annotated[list[str], Field(min_length=1)]
    event_type: str
    venue: str
    address: str
    city: str
    country: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_at: datetime
    end_at: datetime
    capacity: Annotated[int, Field(gt=0)]
    ticket_types: Annotated[list[TicketTypeCreate], Field(min_length=1)]
    description: str
    media: list[str] = []

    @field_validator("end_at")
    @classmethod
    def end_after_start(cls, value: datetime, info):
        if "start_at" in info.data and value <= info.data["start_at"]:
            raise ValueError("end_at must be after start_at")
        return value


class EventUpdate(BaseModel):
    title: str | None = None
    event_type: str | None = None
    venue: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str | None = None
    media: list[str] | None = None

    @field_validator("end_at")
    @classmethod
    def updated_end_after_start(cls, value: datetime, info):
        start_at = info.data.get("start_at")
        if start_at is not None and value <= start_at:
            raise ValueError("end_at must be after start_at")
        return value


class TicketTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price: Decimal
    quantity: int
    available: int


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    event_type: str
    venue: str
    address: str
    city: str
    country: str
    latitude: Decimal | None
    longitude: Decimal | None
    start_at: datetime
    end_at: datetime
    capacity: int
    status: EventStatus
    description: str
    organizer_id: str
    media: list[str] = []
    ticket_types: list[TicketTypeResponse]

    @field_validator("media", mode="before")
    @classmethod
    def extract_media_urls(cls, value):
        return [item.url if hasattr(item, "url") else item for item in value]


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int


class BookingCreate(BaseModel):
    ticket_type_id: str
    number_of_tickets: Annotated[int, Field(gt=0)]


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    attendee_id: str
    ticket_type_id: str
    number_of_tickets: int
    total_cost: Decimal
    status: BookingStatus
    created_at: datetime


class OrganizerBookingResponse(BaseModel):
    id: str
    attendee_id: str
    attendee_username: str
    ticket_type_id: str
    ticket_type_name: str
    number_of_tickets: int
    total_cost: Decimal
    status: BookingStatus
    created_at: datetime


class MessageCreate(BaseModel):
    event_id: str
    recipient_id: str
    body: Annotated[str, Field(min_length=1, max_length=5000)]


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    event_title: str
    sender_id: str
    sender_username: str
    recipient_id: str
    recipient_username: str
    body: str
    is_read: bool
    created_at: datetime


class RecommendationResponse(BaseModel):
    event_id: str
    title: str
    score: float
    reason: str