from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Booking, BookingStatus, Category, Event, EventMedia, EventStatus, Message, TicketType, User, UserRole
from ..schemas import EventCreate, EventListResponse, EventResponse, EventUpdate, OrganizerBookingResponse
from ..security import require_roles

router = APIRouter(prefix="/api/events", tags=["events"])


def event_query():
    return select(Event).options(
        selectinload(Event.ticket_types),
        selectinload(Event.categories),
        selectinload(Event.media),
    )


@router.get("", response_model=EventListResponse)
def list_events(
    search: str | None = Query(default=None, min_length=1),
    city: str | None = None,
    category: str | None = None,
    location: str | None = Query(default=None, min_length=1),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = event_query().where(Event.status == EventStatus.PUBLISHED)
    if search:
        query = query.where(Event.title.ilike(f"%{search}%") | Event.description.ilike(f"%{search}%"))
    if city:
        query = query.where(Event.city.ilike(city))
    if category:
        query = query.join(Event.categories).where(Category.name.ilike(category))
    if location:
        pattern = f"%{location}%"
        query = query.where(
            Event.city.ilike(pattern) | Event.country.ilike(pattern)
            | Event.venue.ilike(pattern) | Event.address.ilike(pattern)
        )
    if date_from:
        query = query.where(Event.start_at >= date_from)
    if date_to:
        query = query.where(Event.start_at <= date_to)
    if min_price is not None or max_price is not None:
        query = query.join(Event.ticket_types)
        if min_price is not None:
            query = query.where(TicketType.price >= min_price)
        if max_price is not None:
            query = query.where(TicketType.price <= max_price)

    total = db.scalar(select(func.count()).select_from(query.with_only_columns(Event.id).distinct().subquery())) or 0
    paged_query = query.order_by(Event.start_at).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(paged_query).unique().all())
    return EventListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.scalar(event_query().where(Event.id == event_id))
    if event is None or event.status not in (EventStatus.PUBLISHED, EventStatus.COMPLETED):
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    if sum(ticket.quantity for ticket in payload.ticket_types) > payload.capacity:
        raise HTTPException(status_code=422, detail="Ticket quantities cannot exceed event capacity")
    category_models = []
    for category_name in set(payload.categories):
        category = db.scalar(select(Category).where(Category.name == category_name))
        if category is None:
            category = Category(name=category_name)
            db.add(category)
        category_models.append(category)
    event = Event(
        title=payload.title,
        event_type=payload.event_type,
        venue=payload.venue,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        start_at=payload.start_at,
        end_at=payload.end_at,
        capacity=payload.capacity,
        description=payload.description,
        organizer_id=organizer.id,
        categories=category_models,
        ticket_types=[TicketType(name=t.name, price=t.price, quantity=t.quantity, available=t.quantity) for t in payload.ticket_types],
        media=[EventMedia(url=url) for url in payload.media],
    )
    db.add(event)
    db.commit()
    return db.scalar(event_query().where(Event.id == event.id))


@router.post("/{event_id}/publish", response_model=EventResponse)
def publish_event(
    event_id: str,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    event = db.scalar(event_query().where(Event.id == event_id, Event.organizer_id == organizer.id))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != EventStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft events can be published")
    event.status = EventStatus.PUBLISHED
    db.commit()
    return event


@router.get("/organizer/mine", response_model=list[EventResponse])
def list_my_events(
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    return list(db.scalars(event_query().where(Event.organizer_id == organizer.id).order_by(Event.created_at.desc())).unique().all())


def owned_event(event_id: str, organizer: User, db: Session) -> Event:
    event = db.scalar(event_query().where(Event.id == event_id, Event.organizer_id == organizer.id))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    event = owned_event(event_id, organizer, db)
    if event.status in (EventStatus.CANCELLED, EventStatus.COMPLETED):
        raise HTTPException(status_code=409, detail="This event can no longer be edited")
    changes = payload.model_dump(exclude_unset=True)
    media_urls = changes.pop("media", None)
    start_at = changes.get("start_at", event.start_at)
    end_at = changes.get("end_at", event.end_at)
    if end_at <= start_at:
        raise HTTPException(status_code=422, detail="end_at must be after start_at")
    for field, value in changes.items():
        setattr(event, field, value)
    if media_urls is not None:
        event.media = [EventMedia(url=url) for url in media_urls]
    db.commit()
    return db.scalar(event_query().where(Event.id == event.id))


@router.post("/{event_id}/cancel", response_model=EventResponse)
def cancel_event(
    event_id: str,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    event = owned_event(event_id, organizer, db)
    if event.status != EventStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Only published events can be cancelled")
    event.status = EventStatus.CANCELLED
    attendee_ids = set(db.scalars(
        select(Booking.attendee_id).where(Booking.event_id == event.id, Booking.status == BookingStatus.CONFIRMED)
    ).all())
    for attendee_id in attendee_ids:
        db.add(Message(
            event_id=event.id,
            sender_id=organizer.id,
            recipient_id=attendee_id,
            body=f'The event "{event.title}" has been cancelled by the organizer.',
        ))
    db.commit()
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    event = owned_event(event_id, organizer, db)
    booking_count = db.scalar(select(func.count(Booking.id)).where(Booking.event_id == event.id)) or 0
    if event.status != EventStatus.DRAFT and booking_count > 0:
        raise HTTPException(status_code=409, detail="Events with bookings cannot be deleted")
    db.delete(event)
    db.commit()


@router.get("/{event_id}/bookings", response_model=list[OrganizerBookingResponse])
def list_event_bookings(
    event_id: str,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER)),
):
    owned_event(event_id, organizer, db)
    rows = db.execute(
        select(Booking, User.username, TicketType.name)
        .join(User, User.id == Booking.attendee_id)
        .join(TicketType, TicketType.id == Booking.ticket_type_id)
        .where(Booking.event_id == event_id)
        .order_by(Booking.created_at.desc())
    ).all()
    return [
        OrganizerBookingResponse(
            id=booking.id,
            attendee_id=booking.attendee_id,
            attendee_username=username,
            ticket_type_id=booking.ticket_type_id,
            ticket_type_name=ticket_type_name,
            number_of_tickets=booking.number_of_tickets,
            total_cost=booking.total_cost,
            status=booking.status,
            created_at=booking.created_at,
        )
        for booking, username, ticket_type_name in rows
    ]