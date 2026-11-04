import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.main import app
from app.models import GuardianSession
from app.services.safety_score import ReporteLike, compute_isn


@pytest.fixture(scope="module")
def client():
    # Sin el "with", TestClient no ejecuta el lifespan (creación de tablas y semilla)
    with TestClient(app) as c:
        yield c


def _auth_headers(client) -> dict:
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": email, "name": "Usuaria", "password": "clave12345"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "clave12345"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_login_and_me(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Usuaria de prueba", "password": "clave12345"},
    )
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", data={"username": email, "password": "clave12345"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


def test_safe_points_near_bogota(client):
    resp = client.get("/api/safe-points", params={"lat": 4.6482, "lng": -74.0648, "radius": 2000})
    assert resp.status_code == 200
    points = resp.json()
    assert isinstance(points, list)
    assert len(points) >= 1


def test_create_and_list_report(client):
    resp = client.post(
        "/api/reports",
        json={"type": "poca_luz", "severity": 3, "description": "Calle oscura", "lat": 4.65, "lng": -74.06},
    )
    assert resp.status_code == 201

    resp = client.get(
        "/api/reports",
        params={"min_lat": 4.0, "max_lat": 5.0, "min_lng": -75.0, "max_lng": -73.0},
    )
    assert resp.status_code == 200
    assert any(r["type"] == "poca_luz" for r in resp.json())


def test_safety_score_penalizes_recent_harassment_report():
    route = [(4.60, -74.08), (4.601, -74.081), (4.602, -74.082)]
    now = datetime.now(timezone.utc)

    sin_riesgo = compute_isn(route, [], [], now=now)
    reporte_acoso = ReporteLike(type="acoso", severity=5, lat=4.601, lng=-74.081, created_at=now)
    con_riesgo = compute_isn(route, [reporte_acoso], [], now=now)

    assert con_riesgo["isn"] < sin_riesgo["isn"]
    assert "acoso" in con_riesgo["breakdown"]["explicacion"]


def test_guardian_and_sos_lifecycle(client):
    headers = _auth_headers(client)

    resp = client.post("/api/contacts", json={"name": "Mamá", "phone": "3001234567"}, headers=headers)
    assert resp.status_code == 201

    resp = client.post("/api/guardian/start", json={"minutes": 20, "lat": 4.65, "lng": -74.06}, headers=headers)
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp = client.post(f"/api/guardian/{session_id}/checkin", json={"lat": 4.651, "lng": -74.061}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = client.post(f"/api/guardian/{session_id}/arrived", headers=headers)
    assert resp.json()["status"] == "arrived"

    resp = client.post("/api/sos", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["contactos_notificados"] == ["3001234567"]


def test_guardian_pasa_a_alerta_al_vencer_eta(client):
    headers = _auth_headers(client)
    resp = client.post("/api/guardian/start", json={"minutes": 20, "lat": 4.65, "lng": -74.06}, headers=headers)
    session_id = resp.json()["id"]

    with SessionLocal() as db:
        db.get(GuardianSession, session_id).eta_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    resp = client.get(f"/api/guardian/{session_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "alert"
