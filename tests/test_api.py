from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.safety_score import ReporteLike, compute_isn

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_safety_score_penalizes_recent_harassment_report():
    route = [(4.60, -74.08), (4.601, -74.081), (4.602, -74.082)]
    now = datetime.now(timezone.utc)

    sin_riesgo = compute_isn(route, [], [], now=now)
    reporte_acoso = ReporteLike(type="acoso", severity=5, lat=4.601, lng=-74.081, created_at=now)
    con_riesgo = compute_isn(route, [reporte_acoso], [], now=now)

    assert con_riesgo["isn"] < sin_riesgo["isn"]
    assert "acoso" in con_riesgo["breakdown"]["explicacion"]
