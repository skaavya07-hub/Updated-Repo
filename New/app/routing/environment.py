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


class OpenMeteoEnvironmentProvider:
    """Open-Meteo wind/marine adapter with bounded requests and an in-memory cache."""

    _cache = {}
    _cache_lock = threading.Lock()
    _cache_ttl_seconds = 1800

    def __init__(self):
        self.weather_url = os.getenv("OPEN_METEO_WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
        self.marine_url = os.getenv("OPEN_METEO_MARINE_URL", "https://marine-api.open-meteo.com/v1/marine")
        self.timeout = float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "4"))

    @staticmethod
    def _nearest(hourly: dict, variable: str, when: datetime):
        times = hourly.get("time") or []
        values = hourly.get(variable) or []
        if not times or not values:
            raise ValueError(f"Open-Meteo response omitted {variable}")
        target = when.astimezone(timezone.utc).replace(tzinfo=None)
        parsed = [datetime.fromisoformat(value) for value in times]
        if target < parsed[0] or target > parsed[-1]:
            raise ValueError("Requested time is outside the available Open-Meteo forecast window")
        index = min(range(len(parsed)), key=lambda i: abs((parsed[i] - target).total_seconds()))
        value = values[index]
        if value is None:
            raise ValueError(f"Open-Meteo returned no value for {variable}")
        return float(value)

    def conditions(self, lat: float, lng: float, when: datetime) -> Conditions:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        cache_key = (round(lat, 2), round(lng, 2), when.astimezone(timezone.utc).strftime("%Y-%m-%d-%H"))
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < self._cache_ttl_seconds:
                return cached[1]

        common = {"latitude": lat, "longitude": lng, "timezone": "UTC", "forecast_days": 16}
        weather_params = {
            **common,
            "hourly": "wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "ms",
        }
        marine_params = {
            **common,
            "hourly": "wave_height,wave_direction,ocean_current_velocity,ocean_current_direction",
        }
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            weather_response = client.get(self.weather_url, params=weather_params)
            marine_response = client.get(self.marine_url, params=marine_params)
            weather_response.raise_for_status()
            marine_response.raise_for_status()
        weather = weather_response.json().get("hourly", {})
        marine = marine_response.json().get("hourly", {})
        result = Conditions(
            wind_ms=self._nearest(weather, "wind_speed_10m", when),
            wind_dir=self._nearest(weather, "wind_direction_10m", when),
            wave_m=self._nearest(marine, "wave_height", when),
            wave_dir=self._nearest(marine, "wave_direction", when),
            current_kn=self._nearest(marine, "ocean_current_velocity", when) / 1.852,
            current_dir=self._nearest(marine, "ocean_current_direction", when),
            source="Open-Meteo weather and marine forecast",
        )
        with self._cache_lock:
            self._cache[cache_key] = (time.monotonic(), result)
        return result


class EnvironmentProvider:
    """Routing facade: live forecast when explicitly enabled, fallback on any failure."""

    def __init__(self, allow_live=None):
        if allow_live is None:
            allow_live = os.getenv("OPEN_METEO_ROUTING_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.allow_live = allow_live and os.getenv("OPEN_METEO_ENABLED", "true").lower() in {"1", "true", "yes"}
        self.live = OpenMeteoEnvironmentProvider()
        self.fallback = DeterministicEnvironmentProvider()

    def conditions(self, lat: float, lng: float, when: datetime, enabled=True) -> Conditions:
        when_utc = when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)
        forecast_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        live_window = forecast_start <= when_utc < forecast_start + timedelta(days=16)
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
