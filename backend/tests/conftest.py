from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.db import get_db


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    main_module.engine = test_engine
    main_module.SessionLocal = TestSessionLocal

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.app.dependency_overrides.clear()


def register_and_approve(client: TestClient, username: str, role: str, password: str = "Password123") -> str:
    response = client.post("/api/auth/register", json={
        "username": username,
        "password": password,
        "password_confirmation": password,
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}@example.com",
        "phone": "1234567890",
        "address": "1 Main St",
        "city": "Athens",
        "country": "Greece",
        "tax_id": f"TAX-{username}",
        "requested_role": role,
    })
    assert response.status_code == 201, response.text

    admin_token = login(client, "admin", "admin123!")
    users = client.get("/api/admin/users?status=pending", headers=auth_headers(admin_token)).json()
    user_id = next(user["id"] for user in users if user["username"] == username)
    approve_response = client.post(f"/api/admin/users/{user_id}/approve", headers=auth_headers(admin_token))
    assert approve_response.status_code == 200

    return login(client, username, password)


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_draft_event(client: TestClient, organizer_token: str, capacity: int, ticket_quantity: int) -> dict:
    response = client.post("/api/events", headers=auth_headers(organizer_token), json={
        "title": "Sample Concert",
        "categories": ["Music"],
        "event_type": "Concert",
        "venue": "City Hall",
        "address": "1 Main St",
        "city": "Athens",
        "country": "Greece",
        "start_at": "2026-07-12T20:30:00",
        "end_at": "2026-07-12T23:00:00",
        "capacity": capacity,
        "description": "A test event",
        "ticket_types": [{"name": "General", "price": "10.00", "quantity": ticket_quantity}],
    })
    assert response.status_code == 201, response.text
    return response.json()
