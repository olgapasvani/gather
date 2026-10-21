from fastapi.testclient import TestClient

from tests.conftest import auth_headers, create_draft_event, register_and_approve


def test_event_search_returns_paginated_envelope(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_search1", "organizer")
    for index in range(3):
        event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
        client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))

    response = client.get("/api/events", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2

    second_page = client.get("/api/events", params={"page": 2, "page_size": 2}).json()
    assert len(second_page["items"]) == 1


def test_event_search_filters_by_price_range(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_search2", "organizer")
    cheap_event = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Cheap Event", "categories": ["Music"], "event_type": "Concert",
        "venue": "Hall", "address": "1 Main St", "city": "Athens", "country": "Greece",
        "start_at": "2026-07-12T20:30:00", "end_at": "2026-07-12T23:00:00", "capacity": 10,
        "description": "desc", "ticket_types": [{"name": "General", "price": "5.00", "quantity": 10}],
    }).json()
    expensive_event = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Expensive Event", "categories": ["Music"], "event_type": "Concert",
        "venue": "Hall", "address": "1 Main St", "city": "Athens", "country": "Greece",
        "start_at": "2026-07-12T20:30:00", "end_at": "2026-07-12T23:00:00", "capacity": 10,
        "description": "desc", "ticket_types": [{"name": "VIP", "price": "500.00", "quantity": 10}],
    }).json()
    client.post(f"/api/events/{cheap_event['id']}/publish", headers=auth_headers(organizer_token))
    client.post(f"/api/events/{expensive_event['id']}/publish", headers=auth_headers(organizer_token))

    response = client.get("/api/events", params={"max_price": "10.00"})
    body = response.json()
    event_ids = [item["id"] for item in body["items"]]
    assert cheap_event["id"] in event_ids
    assert expensive_event["id"] not in event_ids


def test_event_search_filters_by_date_range(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_search3", "organizer")
    early_event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{early_event['id']}/publish", headers=auth_headers(organizer_token))

    response = client.get("/api/events", params={"date_from": "2026-08-01T00:00:00"})
    body = response.json()
    event_ids = [item["id"] for item in body["items"]]
    assert early_event["id"] not in event_ids


def test_event_search_filters_by_location_text(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_search4", "organizer")
    event = create_draft_event(client, organizer_token, capacity=10, ticket_quantity=10)
    client.post(f"/api/events/{event['id']}/publish", headers=auth_headers(organizer_token))

    response = client.get("/api/events", params={"location": "Athens"})
    event_ids = [item["id"] for item in response.json()["items"]]
    assert event["id"] in event_ids

    no_match = client.get("/api/events", params={"location": "Nonexistent City"})
    assert no_match.json()["items"] == []
