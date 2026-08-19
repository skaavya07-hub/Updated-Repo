from dataclasses import dataclass


@dataclass(frozen=True)
class ShipProfile:
    key: str
    label: str
    description: str
    fuel_bias: float
    time_bias: float
    safety_bias: float
    resistance_multiplier: float
    weather_sensitivity: float
    alert_sensitivity: float
    operating_margin: float
    speed_ratios: tuple[float, ...]


SHIP_PROFILES = {
    "general_cargo": ShipProfile("general_cargo", "General cargo", "Balanced routing for conventional cargo operations.", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, (0.68, 0.78, 0.88, 0.96, 1.03)),
    "container": ShipProfile("container", "Container ship", "Schedule-aware routing with balanced fuel and safety exposure.", 0.95, 1.15, 1.0, 0.98, 1.0, 1.0, 1.0, (0.70, 0.80, 0.90, 0.98, 1.04)),
    "bulk_carrier": ShipProfile("bulk_carrier", "Bulk carrier", "Fuel-conscious routing with added draft and heavy-weather caution.", 1.2, 0.8, 1.15, 1.08, 1.2, 1.1, 0.95, (0.62, 0.72, 0.82, 0.90, 0.96)),
    "tanker": ShipProfile("tanker", "Oil / chemical tanker", "Conservative routing around conflict zones and severe weather.", 1.05, 0.9, 1.4, 1.06, 1.2, 1.4, 0.92, (0.64, 0.74, 0.84, 0.92, 0.98)),
    "lng_carrier": ShipProfile("lng_carrier", "LNG carrier", "High-safety routing with strong alert-zone and weather avoidance.", 1.0, 1.0, 1.55, 1.03, 1.3, 1.55, 0.90, (0.68, 0.78, 0.88, 0.96, 1.02)),
    "roro": ShipProfile("roro", "Ro-Ro vessel", "Wind-sensitive routing with additional stability margins.", 0.95, 1.1, 1.3, 1.04, 1.45, 1.1, 0.85, (0.68, 0.78, 0.88, 0.96, 1.02)),
    "passenger": ShipProfile("passenger", "Passenger / cruise", "Comfort- and safety-led routing that strongly avoids rough conditions.", 0.85, 1.15, 1.55, 1.02, 1.55, 1.25, 0.80, (0.72, 0.82, 0.92, 1.0, 1.04)),
}


def get_ship_profile(ship_type: str) -> ShipProfile:
    return SHIP_PROFILES[ship_type]


def public_ship_profiles():
    return [
        {"key": profile.key, "label": profile.label, "description": profile.description}
        for profile in SHIP_PROFILES.values()
    ]
