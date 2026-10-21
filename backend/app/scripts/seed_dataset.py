from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

from ..db import Base, SessionLocal, engine
from ..models import AccountStatus, Booking, BookingStatus, Category, Event, EventStatus, EventView, TicketType, User, UserRole
from ..security import hash_password


DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "rel_event_csvs"


def rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def parse_datetime(value: str | None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value.replace(".003", ".003000"))
        except ValueError:
            pass
    return datetime(2026, 12, 31, 18, 0)


def seed_dataset(dataset_dir: Path, event_limit: int, user_limit: int) -> tuple[int, int, int]:
    Base.metadata.create_all(bind=engine)

    positive_interactions: list[tuple[str, str, str]] = []
    for row in rows(dataset_dir / "event_interest.csv"):
        user_id = row.get("user", "").strip()
        event_id = row.get("event", "").strip()
        if user_id and event_id and (row.get("interested") == "1" or row.get("invited") == "1"):
            positive_interactions.append((user_id, event_id, row.get("timestamp", "")))
            if len(positive_interactions) >= event_limit * 3:
                break

    selected_event_ids: list[str] = []
    for _, event_id, _ in positive_interactions:
        if event_id not in selected_event_ids:
            selected_event_ids.append(event_id)
        if len(selected_event_ids) >= event_limit:
            break

    event_rows: dict[str, dict[str, str]] = {}
    for row in rows(dataset_dir / "events.csv"):
        event_id = row.get("event_id", "").strip()
        if event_id in selected_event_ids:
            event_rows[event_id] = row
        if len(event_rows) == len(selected_event_ids):
            break

    selected_user_ids: list[str] = []
    for user_id, _, _ in positive_interactions:
        if user_id not in selected_user_ids:
            selected_user_ids.append(user_id)
        if len(selected_user_ids) >= user_limit:
            break

    user_rows: dict[str, dict[str, str]] = {}
    for row in rows(dataset_dir / "users.csv"):
        user_id = row.get("user_id", "").strip()
        if user_id in selected_user_ids:
            user_rows[user_id] = row
        if len(user_rows) == len(selected_user_ids):
            break

    created_events = created_users = created_interactions = 0
    with SessionLocal() as db:
        dataset_users: dict[str, User] = {}
        for source_id in selected_user_ids:
            username = f"dataset_user_{source_id}"
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                source = user_rows.get(source_id, {})
                user = User(
                    username=username,
                    password_hash=hash_password(f"dataset_{source_id}!"),
                    first_name="Dataset",
                    last_name=f"User {source_id}",
                    email=f"dataset.{source_id}@example.com",
                    phone="0000000000",
                    address=source.get("location") or "Dataset location",
                    city=(source.get("location") or "Dataset").split(",")[0],
                    country="Dataset",
                    tax_id=f"DATASET-{source_id}",
                    role=UserRole.PARTICIPANT,
                    status=AccountStatus.APPROVED,
                )
                db.add(user)
                created_users += 1
            dataset_users[source_id] = user
        db.flush()

        category = db.scalar(select(Category).where(Category.name == "Dataset events"))
        if category is None:
            category = Category(name="Dataset events")
            db.add(category)
        db.flush()

        dataset_events: dict[str, Event] = {}
        for source_id in selected_event_ids:
            source = event_rows.get(source_id)
            if source is None:
                continue
            username = "dataset_organizer"
            organizer = db.scalar(select(User).where(User.username == username))
            if organizer is None:
                organizer = User(
                    username=username,
                    password_hash=hash_password("dataset_organizer123!"),
                    first_name="Dataset",
                    last_name="Organizer",
                    email="dataset.organizer@example.com",
                    phone="0000000000",
                    address="Dataset",
                    city=source.get("city") or "Dataset",
                    country=source.get("country") or "Dataset",
                    tax_id="DATASET-ORGANIZER",
                    role=UserRole.ORGANIZER,
                    status=AccountStatus.APPROVED,
                )
                db.add(organizer)
                db.flush()
            event = db.scalar(select(Event).where(Event.title == f"Dataset Event {source_id}"))
            if event is None:
                event = Event(
                    title=f"Dataset Event {source_id}",
                    event_type="Dataset event",
                    venue=source.get("city") or "Dataset venue",
                    address=source.get("state") or "Dataset address",
                    city=source.get("city") or "Dataset",
                    country=source.get("country") or "Dataset",
                    latitude=Decimal(source["lat"]) if source.get("lat") else None,
                    longitude=Decimal(source["lng"]) if source.get("lng") else None,
                    start_at=parse_datetime(source.get("start_time")),
                    end_at=parse_datetime(source.get("start_time")) + timedelta(hours=2),
                    capacity=100,
                    status=EventStatus.PUBLISHED,
                    description="Event imported from the course recommendation dataset.",
                    organizer_id=organizer.id,
                    categories=[category],
                    ticket_types=[TicketType(name="Dataset ticket", price=Decimal("10.00"), quantity=100, available=100)],
                )
                db.add(event)
                db.flush()
                created_events += 1
            dataset_events[source_id] = event

        for source_user, source_event, timestamp in positive_interactions:
            user = dataset_users.get(source_user)
            event = dataset_events.get(source_event)
            if user is None or event is None:
                continue
            already_viewed = db.scalar(select(EventView).where(EventView.user_id == user.id, EventView.event_id == event.id).limit(1))
            if already_viewed is None:
                db.add(EventView(user_id=user.id, event_id=event.id))
                created_interactions += 1
            ticket = event.ticket_types[0]
            existing_booking = db.scalar(select(Booking).where(Booking.attendee_id == user.id, Booking.event_id == event.id).limit(1))
            if existing_booking is None and created_interactions % 5 == 0 and ticket.available > 0:
                ticket.available -= 1
                db.add(Booking(event_id=event.id, attendee_id=user.id, ticket_type_id=ticket.id, number_of_tickets=1, total_cost=ticket.price, status=BookingStatus.CONFIRMED))
        db.commit()
    return created_events, created_users, created_interactions


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a bounded subset of the course recommendation CSV dataset")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--events", type=int, default=300)
    parser.add_argument("--users", type=int, default=100)
    args = parser.parse_args()
    result = seed_dataset(args.dataset_dir, args.events, args.users)
    print(f"dataset seed complete: events={result[0]} users={result[1]} interactions={result[2]}")


if __name__ == "__main__":
    main()
