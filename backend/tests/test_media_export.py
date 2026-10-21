from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_and_approve


def test_event_can_be_created_with_media_and_exported(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_media1", "organizer")
    admin_token_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123!"})
    admin_token = admin_token_response.json()["access_token"]

    event = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Event With Photos",
        "categories": ["Music"],
        "event_type": "Concert",
        "venue": "Hall",
        "address": "1 Main St",
        "city": "Athens",
        "country": "Greece",
        "start_at": "2026-07-12T20:30:00",
        "end_at": "2026-07-12T23:00:00",
        "capacity": 10,
        "description": "desc",
        "ticket_types": [{"name": "General", "price": "10.00", "quantity": 10}],
        "media": ["https://example.com/cover1.jpg", "https://example.com/hall.jpg"],
    }).json()
    assert event["media"] == ["https://example.com/cover1.jpg", "https://example.com/hall.jpg"]

    json_export = client.get("/api/admin/exports/events.json", headers=auth_headers(admin_token))
    assert json_export.status_code == 200
    exported_event = next(item for item in json_export.json()["Events"] if item["EventID"] == event["id"])
    assert exported_event["Media"] == ["https://example.com/cover1.jpg", "https://example.com/hall.jpg"]

    xml_export = client.get("/api/admin/exports/events.xml", headers=auth_headers(admin_token))
    assert xml_export.status_code == 200
    assert b"<Photo>https://example.com/cover1.jpg</Photo>" in xml_export.content


def test_event_media_can_be_replaced_via_update(client: TestClient):
    organizer_token = register_and_approve(client, "organizer_media2", "organizer")
    event = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Event", "categories": ["Music"], "event_type": "Concert",
        "venue": "Hall", "address": "1 Main St", "city": "Athens", "country": "Greece",
        "start_at": "2026-07-12T20:30:00", "end_at": "2026-07-12T23:00:00", "capacity": 10,
        "description": "desc", "ticket_types": [{"name": "General", "price": "10.00", "quantity": 10}],
        "media": ["https://example.com/old.jpg"],
    }).json()

    response = client.patch(f"/api/events/{event['id']}", headers=auth_headers(organizer_token), json={
        "media": ["https://example.com/new.jpg"],
    })
    assert response.status_code == 200
    assert response.json()["media"] == ["https://example.com/new.jpg"]
