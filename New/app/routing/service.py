import math
import time
from datetime import timedelta

from app.models import LegResult, LegSummary, Point
from app.routing.bidirectional import search
from app.routing.environment import EnvironmentProvider, bearing_deg, relative_component
from app.routing.fuel import segment_performance
from app.routing.graph import edge_is_water, haversine_nm
from app.routing.safety import alert_cost
from app.routing.ship_profiles import get_ship_profile

COLORS = ["#14b8a6", "#38bdf8", "#818cf8", "#f59e0b", "#22d3ee", "#a78bfa", "#fb7185"]


def _interpolate(a, b, max_nm=45):
    count = max(1, math.ceil(haversine_nm(a, b) / max_nm))
    return [Point(lat=a.lat + (b.lat - a.lat) * i / count, lng=a.lng + (b.lng - a.lng) * i / count) for i in range(count)]


def calculate_leg(graph, origin, destination, departure, fuel_start, vessel, priorities, use_weather, use_alerts, avoidance, leg_index=0, prefer_alternate=True):
    env = EnvironmentProvider()
    wf, wt, ws = priorities.normalized()
    profile = get_ship_profile(vessel.ship_type)
    profile_total = wf * profile.fuel_bias + wt * profile.time_bias + ws * profile.safety_bias
    wf, wt, ws = (
        wf * profile.fuel_bias / profile_total,
        wt * profile.time_bias / profile_total,
        ws * profile.safety_bias / profile_total,
    )
    wave_limit = vessel.max_wave_height_m * profile.operating_margin
    wind_limit = vessel.max_wind_speed_ms * profile.operating_margin
    start, goal = graph.port_nodes[origin], graph.port_nodes[destination]
    exposure = set()
    weather_max = {"wave": 0.0, "wind": 0.0, "sources": set()}
    clearance_cache = {}

    def heuristic(node, target):
        return haversine_nm(graph.nodes[node], graph.nodes[target]) * (0.02 * wt + 0.002 * wf)

    def best_edge(u, v, distance, fuel=fuel_start, when=departure):
        a, b = graph.nodes[u], graph.nodes[v]
        edge_key = (u, v)
        if edge_key not in clearance_cache:
            clearance_cache[edge_key] = edge_is_water(a, b)
        if not clearance_cache[edge_key]:
            return None, None, [], True
        bearing = bearing_deg(a, b)
        conditions = env.conditions((a.lat + b.lat) / 2, (a.lng + b.lng) / 2, when, use_weather)
        if use_weather and (conditions.wave_m > wave_limit or conditions.wind_ms > wind_limit):
            return None, conditions, [], True
        alert_penalty, hits, blocked = alert_cost((a.lat + b.lat) / 2, (a.lng + b.lng) / 2, use_alerts, avoidance)
        if blocked:
            return None, conditions, hits, True
        current = relative_component(conditions.current_kn, conditions.current_dir, bearing) if use_weather else 0
        head_wind = -relative_component(conditions.wind_ms, conditions.wind_dir, bearing) if use_weather else 0
        head_wave = max(0, -math.cos(math.radians(conditions.wave_dir - bearing)) * conditions.wave_m) if use_weather else 0
        options = []
        for speed in (vessel.service_speed_kn * x for x in profile.speed_ratios):
            perf = segment_performance(distance, speed, current, head_wind, head_wave, fuel, vessel, profile.resistance_multiplier)
            if perf:
                fuel_norm = perf.fuel_t / max(1, distance * 0.08)
                time_norm = perf.hours / max(1, distance / vessel.service_speed_kn)
                weather_risk = (conditions.wave_m / wave_limit * 0.55 + conditions.wind_ms / wind_limit * 0.45) * profile.weather_sensitivity
                cost = wf * fuel_norm + wt * time_norm + ws * (weather_risk + alert_penalty * 4 * profile.alert_sensitivity)
                options.append((cost, perf))
        return min(options, key=lambda x: x[0]) if options else None, conditions, hits, False

    def edge_cost(u, v, distance):
        option, _, _, blocked = best_edge(u, v, distance)
        return float("inf") if blocked or option is None else option[0] * distance

    primary_path, evaluated = search(graph, start, goal, edge_cost, heuristic)
    node_path = primary_path
    alternate_selected = False
    if prefer_alternate and len(primary_path) > 2:
        primary_edges = set(zip(primary_path, primary_path[1:]))

        def alternate_cost(u, v, distance):
            cost = edge_cost(u, v, distance)
            return cost * 4.0 if (u, v) in primary_edges else cost

        try:
            candidate, alternate_evaluated = search(graph, start, goal, alternate_cost, heuristic)
            evaluated += alternate_evaluated
            primary_distance = sum(haversine_nm(graph.nodes[a], graph.nodes[b]) for a, b in zip(primary_path, primary_path[1:]))
            candidate_distance = sum(haversine_nm(graph.nodes[a], graph.nodes[b]) for a, b in zip(candidate, candidate[1:]))
            changed_edges = set(zip(candidate, candidate[1:])) - primary_edges
            if changed_edges and candidate_distance <= primary_distance * 1.5:
                node_path = candidate
                alternate_selected = True
        except ValueError:
            pass
    current_fuel, current_time = fuel_start, departure
    total_distance = total_fuel = total_hours = 0.0
    safety_weighted = 0.0
    points = []
    for u, v in zip(node_path, node_path[1:]):
        a, b = graph.nodes[u], graph.nodes[v]
        distance = haversine_nm(a, b)
        option, conditions, hits, blocked = best_edge(u, v, distance, current_fuel, current_time)
        if blocked or option is None:
            raise ValueError("A route segment became unsafe under the vessel operating limits")
        _, perf = option
        reserve = vessel.fuel_capacity_t * vessel.fuel_reserve_percent / 100
        if current_fuel - perf.fuel_t < reserve:
            raise ValueError(f"Insufficient fuel: voyage would breach the {vessel.fuel_reserve_percent:g}% reserve")
        current_fuel -= perf.fuel_t
        current_time += timedelta(hours=perf.hours)
        total_distance += distance; total_fuel += perf.fuel_t; total_hours += perf.hours
        weather_max["wave"] = max(weather_max["wave"], conditions.wave_m)
        weather_max["wind"] = max(weather_max["wind"], conditions.wind_ms)
        weather_max["sources"].add(conditions.source)
        exposure.update(hits)
        risk = min(1, (conditions.wave_m / wave_limit * .5 + conditions.wind_ms / wind_limit * .3) * profile.weather_sensitivity + len(hits) * .12 * profile.alert_sensitivity)
        safety_weighted += (100 * (1 - risk)) * distance
        points.extend(_interpolate(a, b))
    points.append(Point(lat=graph.nodes[goal].lat, lng=graph.nodes[goal].lng))
    summary = LegSummary(origin=origin, destination=destination, distance_nm=round(total_distance, 1), fuel_consumed_t=round(total_fuel, 2), voyage_hours=round(total_hours, 2), average_speed_kn=round(total_distance / total_hours, 2), safety_score=round(safety_weighted / total_distance, 1), fuel_remaining_t=round(current_fuel, 2), arrival_eta=current_time)
    return LegResult(origin=origin, destination=destination, color=COLORS[leg_index % len(COLORS)], route=points, summary=summary), evaluated, exposure, weather_max, alternate_selected
