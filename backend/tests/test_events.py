from fastapi.testclient import TestClient

from tests.conftest import auth_headers, create_draft_event, register_and_approve


def test_ticket_quantity_cannot_exceed_capacity(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_cap", "organizer")
    response = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Overcommitted Event",
        "categories": ["Music"],
        "event_type": "Concert",
        "venue": "City Hall",
        "address": "1 Main St",
        "city": "Athens",
        "country": "Greece",
        "start_at": "2026-07-12T20:30:00",
        "end_at": "2026-07-12T23:00:00",
        "capacity": 5,
        "description": "Too many tickets",
        "ticket_types": [{"name": "General", "price": "10.00", "quantity": 10}],
    })
    assert response.status_code == 422


def test_event_lifecycle_publish_cancel(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_life", "organizer")
    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    assert event["status"] == "draft"

    publish = client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"

    cancel = client.post(f"/api/events/{event['id']}/cancel", headers=auth_headers(organizer_token))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


def test_draft_event_without_bookings_can_be_deleted(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_del", "organizer")
    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)

    response = client.delete(f"/api/events/{event['id']}", headers=auth_headers(organizer_token))
    assert response.status_code == 204


def test_event_with_bookings_cannot_be_deleted(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_del2", "organizer")
    participant_token = register_and_approve(client, "participant_del", "participant")

    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))

    ticket_type_id = event["ticket_types"][0]["id"]
    booking = client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 1,
    })
    assert booking.status_code == 201

    delete_response = client.delete(f"/api/events/{event['id']}", headers=auth_headers(organizer_token))
    assert delete_response.status_code == 409


def test_cancelled_event_rejects_new_bookings(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_cancel", "organizer")
    participant_token = register_and_approve(client, "participant_cancel", "participant")

    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))
    client.post(f"/api/events/{event['id']}/cancel", headers=auth_headers(organizer_token))

    ticket_type_id = event["ticket_types"][0]["id"]
    booking = client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 1,
    })
    assert booking.status_code == 409
