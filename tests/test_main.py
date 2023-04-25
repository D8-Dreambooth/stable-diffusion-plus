import json
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert b"Stable-Diffusion Plus" in response.content


def test_login():
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_whoami():
    response = client.get(
        "/whoami",
        headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 401

    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "admin"


def test_logout():
    response = client.get("/logout")
    assert response.status_code == 200
    assert response.cookies.get("Authorization") is None
