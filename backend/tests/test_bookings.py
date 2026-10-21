from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, create_draft_event, register_and_approve


def test_booking_rejected_when_insufficient_availability(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_avail", "organizer")
    participant_token = register_and_approve(client, "participant_avail", "participant")

    event = create_draft_event(client, organizer_token, capacity=5, ticket_quantity=5)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))
    ticket_type_id = event["ticket_types"][0]["id"]

    first = client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 3,
    })
    assert first.status_code == 201
    assert first.json()["total_cost"] == "30.00"

    second = client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
        "ticket_type_id": ticket_type_id,
        "number_of_tickets": 3,
    })
    assert second.status_code == 409


def test_concurrent_bookings_never_oversell_tickets(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_concurrent", "organizer")
    participant_token = register_and_approve(client, "participant_concurrent", "participant")

    capacity = 10
    event = create_draft_event(client, organizer_token, capacity=capacity, ticket_quantity=capacity)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))
    ticket_type_id = event["ticket_types"][0]["id"]

    attempts = capacity * 3  # far more concurrent requests than available tickets

    def attempt_booking(_: int):
        return client.post(f"/api/events/{event['id']}/bookings", headers=auth_headers(participant_token), json={
            "ticket_type_id": ticket_type_id,
            "number_of_tickets": 1,
        })

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(attempt_booking, range(attempts)))

    successes = [response for response in responses if response.status_code == 201]
    failures = [response for response in responses if response.status_code == 409]

    assert len(successes) == capacity
    assert len(failures) == attempts - capacity

    event_after = client.get(f"/api/events/{event['id']}").json()
    ticket_after = event_after["ticket_types"][0]
    assert ticket_after["available"] == 0
    assert ticket_after["quantity"] == capacity
