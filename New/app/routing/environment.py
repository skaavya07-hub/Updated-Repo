import hashlib
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

# pyrefly: ignore [missing-import]
import httpx


@dataclass
class Conditions:
    wind_ms: float
    wind_dir: float
    wave_m: float
    wave_dir: float
    current_kn: float
    current_dir: float
    source: str = "Deterministic climatological fallback"

    def public_dict(self):
        return asdict(self)


class DeterministicEnvironmentProvider:
    """Stable, time-indexed fallback that requires no network connection."""

    def conditions(self, lat: float, lng: float, when: datetime) -> Conditions:
        key = f"{lat:.2f}:{lng:.2f}:{when:%Y-%m-%d-%H}".encode()
        seed = int(hashlib.sha256(key).hexdigest()[:8], 16)
        seasonal = math.sin((when.timetuple().tm_yday / 365) * math.tau)
        wind = 5.0 + (seed % 700) / 100 + abs(seasonal) * 2.0
        wave = 0.7 + ((seed >> 6) % 220) / 100 + abs(seasonal) * 0.5
        return Conditions(
            wind, seed % 360, wave, (seed >> 9) % 360,
            0.1 + ((seed >> 12) % 90) / 100, (seed >> 18) % 360,
        )


class OpenWeatherEnvironmentProvider:
    """OpenWeather 5-day wind adapter with deterministic marine conditions."""

    _cache = {}
    _cache_lock = threading.Lock()
    _cache_ttl_seconds = 1800

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
        self.forecast_url = os.getenv("OPENWEATHER_FORECAST_URL", "https://api.openweathermap.org/data/2.5/forecast")
        self.timeout = float(os.getenv("OPENWEATHER_TIMEOUT_SECONDS", "4"))
        self.marine_fallback = DeterministicEnvironmentProvider()

    @staticmethod
    def _nearest(entries: list[dict], when: datetime):
        valid = [entry for entry in entries if entry.get("dt") is not None and entry.get("wind")]
        if not valid:
            raise ValueError("OpenWeather response omitted forecast wind data")
        target = when.astimezone(timezone.utc).replace(tzinfo=None)
        timestamps = [datetime.fromtimestamp(entry["dt"], timezone.utc).replace(tzinfo=None) for entry in valid]
        tolerance = timedelta(hours=3)
        if target < timestamps[0] - tolerance or target > timestamps[-1] + tolerance:
            raise ValueError("Requested time is outside the available OpenWeather forecast window")
        index = min(range(len(timestamps)), key=lambda i: abs((timestamps[i] - target).total_seconds()))
        return valid[index]

    def conditions(self, lat: float, lng: float, when: datetime) -> Conditions:
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is not configured")
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        cache_key = (round(lat, 2), round(lng, 2), when.astimezone(timezone.utc).strftime("%Y-%m-%d-%H"))
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < self._cache_ttl_seconds:
                return cached[1]

        params = {"lat": lat, "lon": lng, "appid": self.api_key, "units": "metric"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.forecast_url, params=params)
            response.raise_for_status()
        entry = self._nearest(response.json().get("list") or [], when)
        wind = entry.get("wind") or {}
        if wind.get("speed") is None:
            raise ValueError("OpenWeather returned no wind speed")
        marine = self.marine_fallback.conditions(lat, lng, when)
        result = Conditions(
            wind_ms=float(wind["speed"]),
            wind_dir=float(wind.get("deg", 0)),
            wave_m=marine.wave_m,
            wave_dir=marine.wave_dir,
            current_kn=marine.current_kn,
            current_dir=marine.current_dir,
            source="OpenWeather 5-day forecast + deterministic marine fallback",
        )
        with self._cache_lock:
            self._cache[cache_key] = (time.monotonic(), result)
        return result


class EnvironmentProvider:
    """Routing facade: live forecast when explicitly enabled, fallback on any failure."""

    def __init__(self, allow_live=None):
        if allow_live is None:
            allow_live = os.getenv("OPENWEATHER_ROUTING_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.live = OpenWeatherEnvironmentProvider()
        enabled = os.getenv("OPENWEATHER_ENABLED", "true").lower() in {"1", "true", "yes"}
        self.allow_live = allow_live and enabled and bool(self.live.api_key)
        self.fallback = DeterministicEnvironmentProvider()

    def conditions(self, lat: float, lng: float, when: datetime, enabled=True) -> Conditions:
        when_utc = when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)
        forecast_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        live_window = forecast_start <= when_utc < forecast_start + timedelta(days=5)
        if enabled and self.allow_live and live_window:
            try:
                return self.live.conditions(lat, lng, when)
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                pass
        return self.fallback.conditions(lat, lng, when)


def relative_component(magnitude, direction, bearing):
    return magnitude * math.cos(math.radians(direction - bearing))


def bearing_deg(a, b):
    y = math.sin(math.radians(b.lng - a.lng)) * math.cos(math.radians(b.lat))
    x = math.cos(math.radians(a.lat)) * math.sin(math.radians(b.lat)) - math.sin(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.cos(math.radians(b.lng - a.lng))
    return (math.degrees(math.atan2(y, x)) + 360) % 360
