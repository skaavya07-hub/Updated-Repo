import math

from app.alerts import ALERT_ZONES


def distance_km(lat1, lng1, lat2, lng2):
    x = math.radians(lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371 * math.sqrt(x * x + y * y)


def alert_cost(lat, lng, enabled=True, strength=0.8):
    if not enabled:
        return 0.0, [], False
    cost, hits, blocked = 0.0, [], False
    for zone in ALERT_ZONES:
        d = distance_km(lat, lng, *zone["center"])
        proximity = max(0.0, 1 - d / (zone["radius_km"] * 2.2))
        if proximity:
            cost += proximity * zone["severity"] * strength
        if d <= zone["radius_km"]:
            hits.append(zone["name"])
            blocked |= zone["critical"]
    return cost, hits, blocked

