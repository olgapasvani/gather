from fastapi.testclient import TestClient

from tests.conftest import auth_headers, create_draft_event, register_and_approve


def test_organizer_can_view_bookings_for_own_event(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_bk1", "organizer")
    participant_token = register_and_approve(client, "participant_bk1", "participant")

    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))
    ticket_type_id = event["ticket_types"][0]["id"]

    booking = client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 2,
    })
    assert booking.status_code == 201

    response = client.get(f"/api/events/{event['id']}/bookings", headers=auth_headers(organizer_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["attendee_username"] == "participant_bk1"
    assert body[0]["ticket_type_name"] == "General"
    assert body[0]["number_of_tickets"] == 2


def test_organizer_cannot_view_bookings_for_other_organizers_event(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_bk2", "organizer")
    other_organizer_token = register_and_approve(client, "organizer_bk3", "organizer")

    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)

    response = client.get(f"/api/events/{event['id']}/bookings", headers=auth_headers(other_organizer_token))
    assert response.status_code == 404
