# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_config_and_ports():
    assert client.get("/api/health").status_code == 200
    assert "googleMapsApiKey" in client.get("/api/config").json()
    assert len(client.get("/api/ports").json()) >= 60


def test_environment_preview_changes_with_selected_time():
    common = {"lat": 15, "lng": 88, "live": "false"}
    first = client.get("/api/environment", params={**common, "at": "2026-08-19T00:00:00Z"})
    second = client.get("/api/environment", params={**common, "at": "2026-08-20T12:00:00Z"})
    assert first.status_code == second.status_code == 200
    assert first.json()["forecast_time"] != second.json()["forecast_time"]
    assert first.json()["conditions"] != second.json()["conditions"]


def test_multi_route_validation_and_success():
    bad = client.post("/api/multi-route", json={"ports": ["INBOM", "INBOM"]})
    assert bad.status_code == 422
    body = {"ports": ["INBOM", "LKCMB"], "use_weather": False, "use_alert_zones": False, "vessel": {"fuel_onboard_t": 9000, "fuel_capacity_t": 10000, "displacement_ex_fuel_t": 38000, "reference_displacement_t": 45000, "engine_mcr_kw": 18000}}
    response = client.post("/api/multi-route", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["voyage_legs"] == 1


def test_vessel_validation():
    response = client.post("/api/multi-route", json={"ports": ["INBOM", "LKCMB"], "vessel": {"fuel_onboard_t": 4000, "fuel_capacity_t": 3000}})
    assert response.status_code == 422
