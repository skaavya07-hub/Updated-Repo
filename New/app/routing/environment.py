import hashlib
import math
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conditions:
    wind_ms: float
    wind_dir: float
    wave_m: float
    wave_dir: float
    current_kn: float
    current_dir: float
    source: str = "Deterministic climatological fallback"


class EnvironmentProvider:
    """Time-indexed provider with deterministic fallback; network forecasts can replace this adapter."""
    def conditions(self, lat: float, lng: float, when: datetime, enabled=True) -> Conditions:
        key = f"{lat:.2f}:{lng:.2f}:{when:%Y-%m-%d-%H}".encode()
        seed = int(hashlib.sha256(key).hexdigest()[:8], 16)
        seasonal = math.sin((when.timetuple().tm_yday / 365) * math.tau)
        wind = 5.0 + (seed % 700) / 100 + abs(seasonal) * 2.0
        wave = 0.7 + ((seed >> 6) % 220) / 100 + abs(seasonal) * 0.5
        return Conditions(wind, seed % 360, wave, (seed >> 9) % 360, 0.1 + ((seed >> 12) % 90) / 100, (seed >> 18) % 360)


def relative_component(magnitude, direction, bearing):
    return magnitude * math.cos(math.radians(direction - bearing))


def bearing_deg(a, b):
    y = math.sin(math.radians(b.lng - a.lng)) * math.cos(math.radians(b.lat))
    x = math.cos(math.radians(a.lat)) * math.sin(math.radians(b.lat)) - math.sin(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.cos(math.radians(b.lng - a.lng))
    return (math.degrees(math.atan2(y, x)) + 360) % 360

