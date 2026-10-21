from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Booking, Event, Message, User
from ..schemas import MessageCreate, MessageResponse
from ..security import get_current_user

router = APIRouter(prefix="/api/messages", tags=["messages"])


def to_response(db: Session, message: Message) -> MessageResponse:
    event = db.get(Event, message.event_id)
    sender = db.get(User, message.sender_id)
    recipient = db.get(User, message.recipient_id)
    return MessageResponse(
        id=message.id,
        event_id=message.event_id,
        event_title=event.title if event else "",
        sender_id=message.sender_id,
        sender_username=sender.username if sender else "",
        recipient_id=message.recipient_id,
        recipient_username=recipient.username if recipient else "",
        body=message.body,
        is_read=message.is_read,
        created_at=message.created_at,
    )


def has_event_relationship(db: Session, event_id: str, first_user: str, second_user: str) -> bool:
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        return False
    return db.scalar(select(Booking.id).where(
        Booking.event_id == event_id,
        Booking.attendee_id.in_([first_user, second_user]),
    ).limit(1)) is not None and event.organizer_id in (first_user, second_user)


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(payload: MessageCreate, db: Session = Depends(get_db), sender: User = Depends(get_current_user)):
    if sender.id == payload.recipient_id:
        raise HTTPException(status_code=422, detail="A user cannot message themselves")
    if not has_event_relationship(db, payload.event_id, sender.id, payload.recipient_id):
        raise HTTPException(status_code=403, detail="Messaging is available only after a booking")
    message = Message(event_id=payload.event_id, sender_id=sender.id, recipient_id=payload.recipient_id, body=payload.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return to_response(db, message)


@router.get("/inbox", response_model=list[MessageResponse])
def inbox(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    messages = list(db.scalars(select(Message).where(Message.recipient_id == user.id, Message.recipient_deleted.is_(False)).order_by(Message.created_at.desc())).all())
    responses = [to_response(db, message) for message in messages]
    for message in messages:
        message.is_read = True
    db.commit()
    return responses


@router.get("/sent", response_model=list[MessageResponse])
def sent(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    messages = list(db.scalars(select(Message).where(Message.sender_id == user.id, Message.sender_deleted.is_(False)).order_by(Message.created_at.desc())).all())
    return [to_response(db, message) for message in messages]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    messages = db.scalars(select(Message).where(Message.recipient_id == user.id, Message.recipient_deleted.is_(False), Message.is_read.is_(False))).all()
    return {"count": len(list(messages))}


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.sender_id == user.id:
        message.sender_deleted = True
    elif message.recipient_id == user.id:
        message.recipient_deleted = True
    else:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    db.commit()