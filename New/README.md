# Samudra Route

A production-oriented hackathon decision-support prototype for continuous multi-port ship routing across the Indian Ocean. It combines a water-validated maritime graph, directional environmental costs, vessel-aware fuel modelling, alert-zone avoidance and a premium React command-centre UI.

> **Safety notice:** This is a hackathon decision-support prototype, not certified navigation software. Alert zones are explicitly labelled prototype/demo data. Always use authoritative charts, notices to mariners, verified forecasts and qualified voyage-planning personnel for operational decisions.

## Features

- 60 offshore harbour-approach ports across the Indian Ocean and connected regions
- Continuous 2–8 port voyages; fuel, displacement and time carry across every leg
- One internal bidirectional heuristic search engine with priorities expressed only as edge-cost weights
- Sampled ocean-only graph edges plus detailed Malacca, Hormuz and Bab-el-Mandeb corridors
- Cubic speed-to-power model, engine limits and tank-dependent displacement
- Directional wind, wave and current effects with deterministic, time-indexed fallback data
- Prototype conflict, piracy, restriction and severe-weather overlays with soft and hard avoidance
- Light Google map, numbered ports, outlined coloured legs and direction arrows
- Responsive results dashboard with total and per-leg summaries

## Windows PowerShell installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and provide `GOOGLE_MAPS_API_KEY`. The key is delivered to the browser through `/api/config`; it is therefore a browser key, not a secret. Restrict it in Google Cloud Console to **Maps JavaScript API**, and add HTTP-referrer restrictions for `http://127.0.0.1:8000/*` and the production origin. Never use an unrestricted key.

Build the included React source after making frontend changes:

```powershell
cd frontend
npm install
npm run build
cd ..
python run.py
```

Open <http://127.0.0.1:8000>. The repository includes a prebuilt `frontend/dist` bundle, so Node.js is not required for normal backend startup.

## React development mode

Run the API in one PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run Vite in another:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` to FastAPI and sends `no-store` headers during development to prevent stale validation code.

## API and tests

The API exposes `GET /api/health`, `/api/config`, `/api/ports` and `POST /api/route`, `/api/multi-route`. Interactive API documentation is at `/docs`.

```powershell
python -m pytest -q
```

## Weather API integration

The modular provider in `app/routing/environment.py` includes a working Open-Meteo adapter for 10 m wind, wave height/direction, and ocean-current velocity/direction. Open-Meteo does not require an API key.

Test a live forecast after starting the server:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/environment?lat=10&lng=75&live=true"
```

Configuration is documented in `.env.example`. Preview calls use live Open-Meteo data when available and report `fallback_used`. Routing defaults to the deterministic provider to stay fast and reproducible. To use live forecasts during route edge evaluation, set:

```env
OPEN_METEO_ENABLED=true
OPEN_METEO_ROUTING_ENABLED=true
```

Restart the backend after changing `.env`. If the external API is unavailable or has no value for the requested forecast time, routing automatically uses the deterministic time-indexed fallback. To integrate another vendor, implement a class with `conditions(lat, lng, when) -> Conditions` and select it in `EnvironmentProvider`; no fuel or routing code needs to change.
