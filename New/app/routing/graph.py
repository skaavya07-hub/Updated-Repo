import math
from dataclasses import dataclass

import numpy as np
from global_land_mask import globe


@dataclass(frozen=True)
class Node:
    id: int
    lat: float
    lng: float


def haversine_nm(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3440.065 * 2 * math.asin(min(1, math.sqrt(h)))


def is_water(lat, lng):
    return bool(globe.is_ocean(lat, lng))


def has_offshore_clearance(lat, lng, radius_deg=0.10):
    """Require an ocean buffer around a point so wide route strokes do not hug/cut coasts."""
    lon_radius = radius_deg / max(0.25, math.cos(math.radians(lat)))
    offsets = ((radius_deg, 0), (-radius_deg, 0), (0, lon_radius), (0, -lon_radius))
    return is_water(lat, lng) and all(is_water(lat + dy, lng + dx) for dy, dx in offsets)


def is_designated_narrow_channel(lat, lng):
    return (
        (25.0 <= lat <= 26.7 and 55.0 <= lng <= 57.0)  # Hormuz
        or (11.4 <= lat <= 13.0 and 42.3 <= lng <= 44.5)  # Bab-el-Mandeb
        or (0.8 <= lat <= 6.3 and 98.3 <= lng <= 104.3)  # Malacca/Singapore
    )


def edge_is_water(a, b, samples=None, enforce_clearance=True):
    if samples is None:
        spacing_nm = 3 if enforce_clearance else 10
        samples = max(8, math.ceil(haversine_nm(a, b) / spacing_nm))
    distance = haversine_nm(a, b)
    fractions = np.linspace(0.0, 1.0, samples + 1)
    lats = a.lat + (b.lat - a.lat) * fractions
    lngs = a.lng + (b.lng - a.lng) * fractions
    if not np.all(globe.is_ocean(lats, lngs)):
        return False
    if enforce_clearance:
        candidates = []
        for i in range(0, samples + 1, 4):
            along_nm = distance * i / samples
            lat, lng = float(lats[i]), float(lngs[i])
            if min(along_nm, distance - along_nm) > 18 and not is_designated_narrow_channel(lat, lng):
                candidates.append((lat, lng))
        if candidates:
            clear_lats = np.asarray([p[0] for p in candidates])
            clear_lngs = np.asarray([p[1] for p in candidates])
            radius = 0.10
            lon_radius = radius / np.maximum(0.25, np.cos(np.radians(clear_lats)))
            check_lats = np.concatenate((clear_lats + radius, clear_lats - radius, clear_lats, clear_lats))
            check_lngs = np.concatenate((clear_lngs, clear_lngs, clear_lngs + lon_radius, clear_lngs - lon_radius))
            if not np.all(globe.is_ocean(check_lats, check_lngs)):
                return False
    return True


CORRIDOR_POINTS = [
    # Arabian Sea and western India
    (25.2, 55.15), (25.4, 55.2), (25.7, 55.4), (26.0, 55.7), (26.2, 56.0),
    (26.3, 56.3), (26.45, 56.35), (26.5, 56.5), (26.4, 56.7), (26.1, 56.6),
    (25.5, 56.8), (25.0, 57.2), (24.5, 58.0),
    (24.0, 59.0), (24.0, 60.0), (22.0, 61.0), (20, 61), (15, 62), (10, 64), (5, 67), (0, 69),
    (23, 66), (20, 68), (16, 70), (12, 72), (8, 74), (4, 76), (0, 78),
    # India / Sri Lanka and Bay of Bengal
    (7.5, 77.5), (5.5, 79), (5.5, 82), (8, 84), (12, 86), (16, 88), (20, 90),
    (5, 85), (0, 88), (-5, 91), (-8, 95),
    # Malacca high resolution
    (6.0, 97.5), (5.7, 98.7), (5.2, 99.2), (4.5, 99.8), (3.8, 100.2), (3.0, 100.7),
    (2.3, 101.5), (1.7, 102.3), (1.2, 103.0), (1.15, 103.3), (1.05, 103.55),
    (1.1, 103.75), (1.1, 104.2), (0, 105), (-3, 106.05), (-6.7, 108.55),
    # East Africa / Mozambique channel / south
    (12.0, 45.0), (12, 47), (13, 49), (13, 52), (14, 55), (12, 57), (9, 56),
    (7, 52), (4, 51), (2, 50), (-1, 47), (-3, 43), (-3.5, 42), (-4, 40.2),
    (-2, 52), (-7, 52), (-12, 53), (-18, 54),
    (-24, 52), (-30, 48), (-35, 40), (-37, 30), (-32, 33), (-25, 37), (-18, 40), (-10, 42), (-3, 44),
    # Open ocean islands and Australia northern/western/southern route
    (-5, 60), (-10, 65), (-15, 70), (-20, 75), (-25, 80), (-30, 88), (-34, 100), (-35, 112),
    (-32, 114), (-25, 110), (-18, 108), (-10, 105), (-5, 100),
    (-12, 120), (-12, 130), (-15, 138), (-22, 153), (-30, 154), (-36, 151.5), (-40, 140), (-40, 128), (-38, 117),
]

GRID_POINTS = [
    (lat, lng)
    for lat in range(-45, 33, 5)
    for lng in range(30, 157, 5)
    if is_water(lat, lng)
]


class MaritimeGraph:
    def __init__(self, ports):
        coords = CORRIDOR_POINTS + GRID_POINTS + [(p["lat"], p["lng"]) for p in ports]
        self.nodes = {i: Node(i, *xy) for i, xy in enumerate(coords)}
        self.adj = {i: [] for i in self.nodes}
        self.port_nodes = {p["code"]: len(CORRIDOR_POINTS) + len(GRID_POINTS) + i for i, p in enumerate(ports)}
        self._connect()

    def _connect(self):
        for i, a in self.nodes.items():
            candidates = sorted((haversine_nm(a, b), j) for j, b in self.nodes.items() if i != j)
            added = 0
            for distance, j in candidates:
                max_span = 520
                if distance > max_span:
                    break
                # Fast centreline mask at startup; the wider offshore-clearance
                # check is cached and enforced while evaluating route edges.
                if edge_is_water(a, self.nodes[j], enforce_clearance=False):
                    self.adj[i].append((j, distance))
                    if all(existing != i for existing, _ in self.adj[j]):
                        self.adj[j].append((i, distance))
                    added += 1
                    if added >= 10:
                        break
