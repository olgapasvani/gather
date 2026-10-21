from collections import defaultdict
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Booking, BookingStatus, Event, EventStatus, EventView


def recommend(db: Session, user_id: str, limit: int = 8) -> list[dict]:
    events = list(db.scalars(select(Event).where(Event.status == EventStatus.PUBLISHED)).all())
    if not events:
        return []
    views = list(db.scalars(select(EventView).where(EventView.user_id == user_id)).all())
    bookings = list(db.scalars(select(Booking).where(Booking.attendee_id == user_id, Booking.status == BookingStatus.CONFIRMED)).all())
    interactions: dict[tuple[str, str], float] = defaultdict(float)
    for view in views:
        interactions[(user_id, view.event_id)] += 1.0
    for booking in bookings:
        interactions[(user_id, booking.event_id)] += 5.0
    seen = {event_id for (_, event_id) in interactions}
    if not interactions:
        return [{"event_id": event.id, "title": event.title, "score": 0.0, "reason": "Popular upcoming event"} for event in events[:limit]]

    users = {user_id}
    users.update(user for user, _ in interactions)
    items = {event.id for event in events}
    user_bias = defaultdict(float)
    item_bias = defaultdict(float)
    user_vector = {user: [0.01 * (index + 1) for index in range(8)] for user in users}
    item_vector = {item: [0.01 * (index + 2) for index in range(8)] for item in items}
    global_mean = sum(interactions.values()) / len(interactions)
    random = Random(7)
    for vector in list(user_vector.values()) + list(item_vector.values()):
        for index in range(len(vector)):
            vector[index] += random.uniform(-0.01, 0.01)
    learning_rate, regularization = 0.02, 0.05
    for _ in range(40):
        for (user, item), rating in interactions.items():
            prediction = global_mean + user_bias[user] + item_bias[item] + sum(a * b for a, b in zip(user_vector[user], item_vector[item]))
            error = rating - prediction
            user_bias[user] += learning_rate * (error - regularization * user_bias[user])
            item_bias[item] += learning_rate * (error - regularization * item_bias[item])
            for index in range(8):
                user_value = user_vector[user][index]
                item_value = item_vector[item][index]
                user_vector[user][index] += learning_rate * (error * item_value - regularization * user_value)
                item_vector[item][index] += learning_rate * (error * user_value - regularization * item_value)

    recommendations = []
    for event in events:
        if event.id in seen:
            continue
        score = global_mean + user_bias[user_id] + item_bias[event.id] + sum(a * b for a, b in zip(user_vector[user_id], item_vector[event.id]))
        recommendations.append({"event_id": event.id, "title": event.title, "score": round(score, 4), "reason": "Based on your event activity"})
    return sorted(recommendations, key=lambda recommendation: recommendation["score"], reverse=True)[:limit]