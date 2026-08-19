ALERT_ZONES = [
    {"id": "gulf-aden", "name": "Gulf of Aden piracy risk", "type": "piracy", "severity": 0.75, "critical": False, "center": [12.2, 48.2], "radius_km": 420},
    {"id": "somalia", "name": "Somali Basin piracy advisory", "type": "piracy", "severity": 0.65, "critical": False, "center": [5.0, 51.0], "radius_km": 430},
    {"id": "red-sea", "name": "Southern Red Sea conflict advisory", "type": "conflict", "severity": 1.0, "critical": True, "center": [15.4, 42.4], "radius_km": 105},
    {"id": "hormuz-lockdown", "name": "Strait of Hormuz Iran–USA conflict lockdown scenario", "type": "conflict", "severity": 1.0, "critical": True, "center": [26.56, 56.25], "radius_km": 160},
    {"id": "malacca", "name": "Malacca traffic caution", "type": "restricted", "severity": 0.3, "critical": False, "center": [3.2, 100.2], "radius_km": 120},
    {"id": "bay-bengal", "name": "Bay of Bengal seasonal severe weather", "type": "weather", "severity": 0.45, "critical": False, "center": [15.0, 88.0], "radius_km": 380},
]
