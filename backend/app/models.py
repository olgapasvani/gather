from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UserRole(StrEnum):
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class AccountStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


event_categories = Table(
    "event_categories",
    Base.metadata,
    Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(40))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    tax_id: Mapped[str] = mapped_column(String(30), unique=True)
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.PARTICIPANT)
    status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.PENDING)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="organizer")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="attendee")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    events: Mapped[list["Event"]] = relationship(secondary=event_categories, back_populates="categories")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    venue: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    country: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column()
    status: Mapped[EventStatus] = mapped_column(String(20), default=EventStatus.DRAFT, index=True)
    description: Mapped[str] = mapped_column(Text)
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organizer: Mapped[User] = relationship(back_populates="events")
    categories: Mapped[list[Category]] = relationship(secondary=event_categories, back_populates="events")
    ticket_types: Mapped[list["TicketType"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="event")
    media: Mapped[list["EventMedia"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class TicketType(Base):
    __tablename__ = "ticket_types"
    __table_args__ = (UniqueConstraint("event_id", "name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column()
    available: Mapped[int] = mapped_column()

    event: Mapped[Event] = relationship(back_populates="ticket_types")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="ticket_type")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    attendee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    ticket_type_id: Mapped[str] = mapped_column(ForeignKey("ticket_types.id"))
    number_of_tickets: Mapped[int] = mapped_column()
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[BookingStatus] = mapped_column(String(20), default=BookingStatus.CONFIRMED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped[Event] = relationship(back_populates="bookings")
    attendee: Mapped[User] = relationship(back_populates="bookings")
    ticket_type: Mapped[TicketType] = relationship(back_populates="bookings")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sender_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    recipient_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EventView(Base):
    __tablename__ = "event_views"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EventMedia(Base):
    __tablename__ = "event_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))

    event: Mapped[Event] = relationship(back_populates="media")