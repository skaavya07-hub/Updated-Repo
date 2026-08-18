import time

from app.models import RouteResponse, TotalSummary
from app.ports import PORT_BY_CODE, public_ports
from app.routing.graph import MaritimeGraph
from app.routing.service import calculate_leg

GRAPH = MaritimeGraph(public_ports())


def calculate_multi(request):
    started = time.perf_counter()
    unknown = [p for p in request.ports if p not in PORT_BY_CODE]
    if unknown:
        raise ValueError(f"Unknown port code: {unknown[0]}")
    request.priorities.normalized()
    fuel, departure = request.vessel.fuel_onboard_t, request.departure_time
    legs, combined, exposure, warnings = [], [], set(), []
    cells = 0; max_wave = max_wind = 0.0; alternate_legs = []; environmental_sources = set()
    for index, (origin, destination) in enumerate(zip(request.ports, request.ports[1:])):
        leg, evaluated, hits, weather, alternate_selected = calculate_leg(GRAPH, origin, destination, departure, fuel, request.vessel, request.priorities, request.use_weather, request.use_alert_zones, request.alert_avoidance, index, request.prefer_alternate_route)
        legs.append(leg); cells += evaluated; exposure.update(hits)
        combined.extend(leg.route if not combined else leg.route[1:])
        fuel = leg.summary.fuel_remaining_t; departure = leg.summary.arrival_eta
        max_wave = max(max_wave, weather["wave"]); max_wind = max(max_wind, weather["wind"])
        environmental_sources.update(weather["sources"])
        if alternate_selected:
            alternate_legs.append(index + 1)
    distance = sum(x.summary.distance_nm for x in legs)
    hours = sum(x.summary.voyage_hours for x in legs)
    consumed = request.vessel.fuel_onboard_t - fuel
    safety = sum(x.summary.safety_score * x.summary.distance_nm for x in legs) / distance
    if exposure:
        warnings.append("Route approaches prototype/demo maritime alert zones; verify against authoritative notices.")
    if request.prefer_alternate_route:
        if alternate_legs:
            warnings.append(f"Alternate water route selected for leg(s): {', '.join(map(str, alternate_legs))}.")
        else:
            warnings.append("No suitable alternate water route was available; the primary optimized route was used.")
    warnings.append("Decision-support prototype only — not certified navigation software.")
    summary = TotalSummary(distance_nm=round(distance, 1), voyage_hours=round(hours, 2), fuel_consumed_t=round(consumed, 2), fuel_remaining_t=round(fuel, 2), average_speed_kn=round(distance / hours, 2), co2_emissions_t=round(consumed * 3.114, 2), safety_score=round(safety, 1), max_wave_height_m=round(max_wave, 2), max_wind_speed_ms=round(max_wind, 2), arrival_eta=departure, cells_evaluated=cells, computation_ms=round((time.perf_counter() - started) * 1000, 1), voyage_legs=len(legs), route_points=len(combined))
    return RouteResponse(combined_route=combined, legs=legs, summary=summary, warnings=warnings, environmental_source="; ".join(sorted(environmental_sources)) or "Weather routing disabled", alert_zone_exposure=sorted(exposure))
