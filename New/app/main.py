import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.alerts import ALERT_ZONES
from app.models import MultiRouteRequest, RouteRequest
from app.ports import public_ports
from app.routing.multi_service import calculate_multi

load_dotenv()
app = FastAPI(title="Samudra Route API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "samudra-route"}


@app.get("/api/config")
def config():
    return {"googleMapsApiKey": os.getenv("GOOGLE_MAPS_API_KEY", ""), "alerts": ALERT_ZONES, "prototype": True}


@app.get("/api/ports")
def ports():
    return public_ports()


@app.post("/api/multi-route")
def multi_route(request: MultiRouteRequest):
    try:
        return calculate_multi(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/route")
def route(request: RouteRequest):
    multi = MultiRouteRequest(ports=[request.origin, request.destination], departure_time=request.departure_time, vessel=request.vessel, priorities=request.priorities, use_weather=request.use_weather, use_alert_zones=request.use_alert_zones, alert_avoidance=request.alert_avoidance)
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

