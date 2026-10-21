from fastapi.testclient import TestClient

from tests.conftest import auth_headers, create_draft_event, register_and_approve


def test_no_recommendations_when_no_published_events(client: TestClient):
    participant_token = register_and_approve(client, "participant_norec", "participant")
    response = client.get("/api/recommendations", headers=auth_headers(participant_token))
    assert response.status_code == 200
    assert response.json() == []


def test_cold_start_falls_back_to_popular_events(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_rec1", "organizer")
    participant_token = register_and_approve(client, "participant_rec1", "participant")

    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))

    response = client.get("/api/recommendations", headers=auth_headers(participant_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["event_id"] == event["id"]
    assert body[0]["reason"] == "Popular upcoming event"
    assert body[0]["score"] == 0.0


def test_booked_events_are_excluded_from_recommendations(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_rec2", "organizer")
    participant_token = register_and_approve(client, "participant_rec2", "participant")

    booked_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{booked_event['id']}/publish", headers=auth_headers(organizer_token))
    other_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{other_event['id']}/publish", headers=auth_headers(organizer_token))

    ticket_type_id = booked_event["ticket_types"][0]["id"]
    booking = client.post(f"/api/events/{booked_event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 1,
    })
    assert booking.status_code == 201

    response = client.get("/api/recommendations", headers=auth_headers(participant_token))
    assert response.status_code == 200
    event_ids = [item["event_id"] for item in response.json()]
    assert booked_event["id"] not in event_ids
    assert other_event["id"] in event_ids


def test_viewed_events_are_recorded_and_excluded(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_rec3", "organizer")
    participant_token = register_and_approve(client, "participant_rec3", "participant")

    viewed_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{viewed_event['id']}/publish", headers=auth_headers(organizer_token))
    other_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{other_event['id']}/publish", headers=auth_headers(organizer_token))

    view_response = client.post(f"/api/events/{viewed_event['id']}/views", headers=auth_headers(participant_token))
    assert view_response.status_code == 201
    assert view_response.json()["recorded"] is True

    response = client.get("/api/recommendations", headers=auth_headers(participant_token))
    assert response.status_code == 200
    event_ids = [item["event_id"] for item in response.json()]
    assert viewed_event["id"] not in event_ids
    assert other_event["id"] in event_ids


def test_view_on_unpublished_event_is_not_recorded(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_rec4", "organizer")
    participant_token = register_and_approve(client, "participant_rec4", "participant")

    draft_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)

    response = client.post(f"/api/events/{draft_event['id']}/views", headers=auth_headers(participant_token))
    assert response.status_code == 201
    assert response.json()["recorded"] is False
