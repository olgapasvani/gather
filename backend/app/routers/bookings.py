from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Booking, BookingStatus, Event, EventStatus, TicketType, User, UserRole
from ..schemas import BookingCreate, BookingResponse
from ..security import require_roles

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/events/{event_id}/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    event_id: str,
    payload: BookingCreate,
    db: Session = Depends(get_db),
    attendee: User = Depends(require_roles(UserRole.PARTICIPANT)),
):
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None or event.status != EventStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="This event is not accepting bookings")

    ticket = db.scalar(select(TicketType).where(TicketType.id == payload.ticket_type_id, TicketType.event_id == event_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket type not found for this event")

    with db.begin_nested():
        result = db.execute(
            update(TicketType)
            .where(TicketType.id == ticket.id, TicketType.available >= payload.number_of_tickets)
            .values(available=TicketType.available - payload.number_of_tickets)
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=409, detail="Not enough tickets available")
        booking = Booking(
            event_id=event_id,
            attendee_id=attendee.id,
            ticket_type_id=ticket.id,
            number_of_tickets=payload.number_of_tickets,
            total_cost=Decimal(ticket.price) * payload.number_of_tickets,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/bookings", response_model=list[BookingResponse])
def list_my_bookings(
    db: Session = Depends(get_db),
    attendee: User = Depends(require_roles(UserRole.PARTICIPANT)),
):
    return list(db.scalars(select(Booking).where(Booking.attendee_id == attendee.id).order_by(Booking.created_at.desc())).all())