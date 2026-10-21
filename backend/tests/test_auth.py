from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login, register_and_approve


def test_register_creates_pending_account(client: TestClient):
    response = client.post("/api/auth/register", json={
        "username": "newuser",
        "password": "Password123",
        "password_confirmation": "Password123",
        "first_name": "New",
        "last_name": "User",
        "email": "newuser@example.com",
        "phone": "1234567890",
        "address": "1 Main St",
        "city": "Athens",
        "country": "Greece",
        "tax_id": "TAX-newuser",
        "requested_role": "participant",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_duplicate_username_is_rejected(client: TestClient):
    payload = {
        "username": "duplicate",
        "password": "Password123",
        "password_confirmation": "Password123",
        "first_name": "A",
        "last_name": "B",
        "email": "a@example.com",
        "phone": "123",
        "address": "addr",
        "city": "Athens",
        "country": "Greece",
        "tax_id": "TAX-1",
        "requested_role": "participant",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    payload["email"] = "different@example.com"
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_password_confirmation_mismatch_is_rejected(client: TestClient):
    response = client.post("/api/auth/register", json={
        "username": "mismatch",
        "password": "Password123",
        "password_confirmation": "Different123",
        "first_name": "A",
        "last_name": "B",
        "email": "mismatch@example.com",
        "phone": "123",
        "address": "addr",
        "city": "Athens",
        "country": "Greece",
        "tax_id": "TAX-2",
        "requested_role": "participant",
    })
    assert response.status_code == 422


def test_login_blocked_until_approved(client: TestClient):
    client.post("/api/auth/register", json={
        "username": "pendinguser",
        "password": "Password123",
        "password_confirmation": "Password123",
        "first_name": "Pending",
        "last_name": "User",
        "email": "pendinguser@example.com",
        "phone": "123",
        "address": "addr",
        "city": "Athens",
        "country": "Greece",
        "tax_id": "TAX-3",
        "requested_role": "participant",
    })
    response = client.post("/api/auth/login", json={"username": "pendinguser", "password": "Password123"})
    assert response.status_code == 403


def test_admin_can_login_with_seeded_credentials(client: TestClient):
    token = login(client, "admin", "admin123!")
    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_admin_approval_allows_login(client: TestClient):
    token = register_and_approve(client, "organizer1", "organizer")
    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["status"] == "approved"
