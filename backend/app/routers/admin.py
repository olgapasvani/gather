import json
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import AccountStatus, Event, User, UserRole
from ..schemas import UserAdminResponse
from ..security import require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_only = require_roles(UserRole.ADMIN)


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    status: AccountStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    query = select(User).order_by(User.created_at.desc())
    if status is not None:
        query = query.where(User.status == status)
    return list(db.scalars(query).all())


@router.get("/users/{user_id}", response_model=UserAdminResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/approve", response_model=UserAdminResponse)
def approve_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = AccountStatus.APPROVED
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reject", response_model=UserAdminResponse)
def reject_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = AccountStatus.REJECTED
    db.commit()
    db.refresh(user)
    return user


def export_events(db: Session):
    query = select(Event).options(
        selectinload(Event.categories),
        selectinload(Event.ticket_types),
        selectinload(Event.bookings),
        selectinload(Event.media),
    )
    return list(db.scalars(query.order_by(Event.created_at)).unique().all())


def event_json(event: Event) -> dict:
    return {
        "EventID": event.id,
        "Title": event.title,
        "Category": [category.name for category in event.categories],
        "EventType": event.event_type,
        "Venue": event.venue,
        "Address": event.address,
        "City": event.city,
        "Country": event.country,
        "GeoLocation": {"Latitude": str(event.latitude), "Longitude": str(event.longitude)} if event.latitude is not None and event.longitude is not None else None,
        "StartDateTime": event.start_at.isoformat(),
        "EndDateTime": event.end_at.isoformat(),
        "Capacity": event.capacity,
        "TicketTypes": [{"TicketTypeID": ticket.id, "Name": ticket.name, "Price": str(ticket.price), "Quantity": ticket.quantity, "Available": ticket.available} for ticket in event.ticket_types],
        "Bookings": [{"BookingID": booking.id, "Attendee": booking.attendee_id, "Time": booking.created_at.isoformat(), "TicketTypeRef": booking.ticket_type_id, "NumberOfTickets": booking.number_of_tickets, "TotalCost": str(booking.total_cost), "BookingStatus": booking.status} for booking in event.bookings],
        "Organizer": event.organizer_id,
        "Status": event.status,
        "Description": event.description,
        "Media": [item.url for item in event.media],
    }


@router.get("/exports/events.json")
def export_events_json(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return JSONResponse(content={"Events": [event_json(event) for event in export_events(db)]})


@router.get("/exports/events.xml")
def export_events_xml(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    root = Element("Events")
    for event in export_events(db):
        data = event_json(event)
        element = SubElement(root, "Event", {"EventID": event.id})
        SubElement(element, "Title").text = data["Title"]
        for category in data["Category"]:
            SubElement(element, "Category").text = category
        for name in ("EventType", "Venue", "Address", "City", "Country"):
            SubElement(element, name).text = data[name]
        if data["GeoLocation"]:
            SubElement(element, "GeoLocation", data["GeoLocation"])
        for name in ("StartDateTime", "EndDateTime", "Capacity"):
            SubElement(element, name).text = str(data[name])
        tickets = SubElement(element, "TicketTypes")
        for ticket in data["TicketTypes"]:
            ticket_element = SubElement(tickets, "TicketType", {"TicketTypeID": ticket["TicketTypeID"]})
            for name in ("Name", "Price", "Quantity", "Available"):
                SubElement(ticket_element, name).text = str(ticket[name])
        bookings = SubElement(element, "Bookings")
        for booking in data["Bookings"]:
            booking_element = SubElement(bookings, "Booking", {"BookingID": booking["BookingID"]})
            SubElement(booking_element, "Attendee", {"UserID": booking["Attendee"]})
            for name in ("Time", "TicketTypeRef", "NumberOfTickets", "TotalCost", "BookingStatus"):
                SubElement(booking_element, name).text = str(booking[name])
        SubElement(element, "Organizer", {"UserID": event.organizer_id})
        SubElement(element, "Status").text = data["Status"]
        SubElement(element, "Description").text = data["Description"]
        if data["Media"]:
            media_element = SubElement(element, "Media")
            for photo_url in data["Media"]:
                SubElement(media_element, "Photo").text = photo_url
    content = tostring(root, encoding="utf-8", xml_declaration=True)
    return StreamingResponse(BytesIO(content), media_type="application/xml", headers={"Content-Disposition": "attachment; filename=events.xml"})