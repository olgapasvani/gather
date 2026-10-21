from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import AccountStatus, Booking, BookingStatus, Category, Event, EventStatus, EventMedia, TicketType, User, UserRole
from .routers import admin, auth, bookings, events, messages, recommendations
from .security import hash_password


def seed_admin() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == settings.admin_username))
        if admin is None:
            db.add(User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                first_name="Application",
                last_name="Administrator",
                email="admin@example.com",
                phone="0000000000",
                address="System",
                city="System",
                country="Greece",
                tax_id="ADMIN-000",
                role=UserRole.ADMIN,
                status=AccountStatus.APPROVED,
            ))
            db.commit()


def seed_demo_data() -> None:
    with SessionLocal() as db:
        organizer = db.scalar(select(User).where(User.username == "demo_organizer"))
        if organizer is None:
            organizer = User(
                username="demo_organizer",
                password_hash=hash_password("organizer123!"),
                first_name="Demo",
                last_name="Organizer",
                email="demo.organizer@example.com",
                phone="2100000000",
                address="Ermou 1",
                city="Athens",
                country="Greece",
                tax_id="DEMO-ORG-001",
                role=UserRole.ORGANIZER,
                status=AccountStatus.APPROVED,
            )
            db.add(organizer)

        participant = db.scalar(select(User).where(User.username == "demo_participant"))
        if participant is None:
            participant = User(
                username="demo_participant",
                password_hash=hash_password("participant123!"),
                first_name="Demo",
                last_name="Participant",
                email="demo.participant@example.com",
                phone="2100000001",
                address="Patission 10",
                city="Athens",
                country="Greece",
                tax_id="DEMO-PAR-001",
                role=UserRole.PARTICIPANT,
                status=AccountStatus.APPROVED,
            )
            db.add(participant)

        pending_users = [
            ("demo_pending_organizer", "pendingorg123!", "Pending", "Organizer", "demo.pending.organizer@example.com", "DEMO-PENDING-ORG", UserRole.ORGANIZER),
            ("demo_pending_participant", "pendingpar123!", "Pending", "Participant", "demo.pending.participant@example.com", "DEMO-PENDING-PAR", UserRole.PARTICIPANT),
        ]
        for username, password, first_name, last_name, email, tax_id, role in pending_users:
            if db.scalar(select(User).where(User.username == username)) is None:
                db.add(User(
                    username=username,
                    password_hash=hash_password(password),
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone="2100000002",
                    address="Pending approval address",
                    city="Athens",
                    country="Greece",
                    tax_id=tax_id,
                    role=role,
                    status=AccountStatus.PENDING,
                ))
        db.flush()

        demo_events = [
            {
                "title": "Athens Contemporary Music Night",
                "category": "Music",
                "event_type": "Concert",
                "venue": "Technopolis City of Athens",
                "address": "Pireos 100",
                "city": "Athens",
                "latitude": Decimal("37.9785"),
                "longitude": Decimal("23.7110"),
                "start_at": datetime(2026, 10, 16, 20, 30),
                "end_at": datetime(2026, 10, 16, 23, 0),
                "capacity": 350,
                "description": "A night of contemporary music with emerging Greek artists.",
                "tickets": [("General Admission", Decimal("18.00"), 250), ("Student", Decimal("12.00"), 100)],
                "media": ["https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=1200"],
            },
            {
                "title": "Product Design Workshop",
                "category": "Workshop",
                "event_type": "Seminar",
                "venue": "The Cube Athens",
                "address": "Kolokynthous 28",
                "city": "Athens",
                "latitude": Decimal("37.9892"),
                "longitude": Decimal("23.7285"),
                "start_at": datetime(2026, 11, 7, 10, 0),
                "end_at": datetime(2026, 11, 7, 16, 0),
                "capacity": 80,
                "description": "A practical workshop on user research, prototyping and product thinking.",
                "tickets": [("Standard", Decimal("35.00"), 60), ("Student", Decimal("20.00"), 20)],
                "media": ["https://images.unsplash.com/photo-1556761175-b413da4baf72?w=1200"],
            },
            {
                "title": "Open Air Theatre Evening",
                "category": "Theatre",
                "event_type": "Theatre Performance",
                "venue": "Theatre of Dionysus",
                "address": "Dionysiou Areopagitou",
                "city": "Athens",
                "latitude": Decimal("37.9709"),
                "longitude": Decimal("23.7278"),
                "start_at": datetime(2026, 9, 30, 21, 0),
                "end_at": datetime(2026, 9, 30, 23, 0),
                "capacity": 120,
                "description": "An open-air performance in one of Athens' historic theatre venues.",
                "tickets": [("General", Decimal("15.00"), 100), ("Premium", Decimal("25.00"), 20)],
                "media": ["https://placehold.co/1200x700?text=Open+Air+Theatre"],
            },
        ]

        for data in demo_events:
            event = db.scalar(select(Event).where(Event.title == data["title"]))
            if event is not None:
                continue
            category = db.scalar(select(Category).where(Category.name == data["category"]))
            if category is None:
                category = Category(name=data["category"])
                db.add(category)
            event = Event(
                title=data["title"], event_type=data["event_type"], venue=data["venue"],
                address=data["address"], city=data["city"], country="Greece",
                latitude=data["latitude"], longitude=data["longitude"],
                start_at=data["start_at"], end_at=data["end_at"], capacity=data["capacity"],
                status=EventStatus.PUBLISHED, description=data["description"],
                organizer_id=organizer.id, categories=[category],
                ticket_types=[TicketType(name=name, price=price, quantity=quantity, available=quantity) for name, price, quantity in data["tickets"]],
                media=[EventMedia(url=url) for url in data["media"]],
            )
            db.add(event)
            db.flush()
            if data["title"] == "Athens Contemporary Music Night":
                ticket = event.ticket_types[0]
                ticket.available -= 2
                db.add(Booking(
                    event_id=event.id, attendee_id=participant.id, ticket_type_id=ticket.id,
                    number_of_tickets=2, total_cost=ticket.price * 2, status=BookingStatus.CONFIRMED,
                ))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    if get_settings().seed_demo_data:
        seed_demo_data()
    yield


app = FastAPI(title="Event Booking API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(admin.router)
app.include_router(bookings.router)
app.include_router(messages.router)
app.include_router(recommendations.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}