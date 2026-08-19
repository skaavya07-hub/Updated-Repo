import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.alerts import ALERT_ZONES
from app.models import MultiRouteRequest, RouteRequest
from app.ports import public_ports
from app.routing.environment import EnvironmentProvider
from app.routing.ship_profiles import public_ship_profiles

load_dotenv()
app = FastAPI(title="Samudra Route API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "samudra-route"}


@app.get("/api/config")
def config():
    return config_payload()


def config_payload():
    weather_provider = "OpenWeather forecast" if os.getenv("OPENWEATHER_API_KEY", "").strip() else "Date-indexed fallback"
    return {"googleMapsApiKey": os.getenv("GOOGLE_MAPS_API_KEY", ""), "weatherProvider": weather_provider, "alerts": ALERT_ZONES, "shipProfiles": public_ship_profiles(), "prototype": True}


@app.get("/api/ports")
def ports():
    return public_ports()


@app.get("/api/bootstrap")
def bootstrap():
    """Return all data needed for the first render in one serverless request."""
    return {**config_payload(), "ports": public_ports()}


@app.get("/api/environment")
def environment_preview(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    at: datetime | None = None,
    live: bool = True,
):
    """Preview live or fallback environmental conditions at a coordinate/time."""
    when = at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    provider = EnvironmentProvider(allow_live=live)
    conditions = provider.conditions(lat, lng, when, enabled=True)
    return {
        "latitude": lat,
        "longitude": lng,
        "forecast_time": when,
        "conditions": conditions.public_dict(),
        "live_requested": live,
        "fallback_used": conditions.source.startswith("Deterministic"),
    }


@app.post("/api/multi-route")
def multi_route(request: MultiRouteRequest):
    # Building the maritime graph is intentionally deferred until a route is
    # requested so map/config startup does not pay that CPU-heavy cost.
    from app.routing.multi_service import calculate_multi

    try:
        return calculate_multi(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/route")
def route(request: RouteRequest):
    from app.routing.multi_service import calculate_multi

    multi = MultiRouteRequest(ports=[request.origin, request.destination], departure_time=request.departure_time, vessel=request.vessel, priorities=request.priorities, use_weather=request.use_weather, use_alert_zones=request.use_alert_zones, alert_avoidance=request.alert_avoidance, prefer_alternate_route=request.prefer_alternate_route)
    try:
        return calculate_multi(multi)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = DIST / path
        return FileResponse(target if target.is_file() else DIST / "index.html", headers={"Cache-Control": "no-cache"})
