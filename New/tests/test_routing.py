from datetime import datetime, timezone

import pytest

from app.models import MultiRouteRequest, Priorities, VesselParameters
from app.routing.environment import OpenMeteoEnvironmentProvider
from app.routing.graph import edge_is_water, has_offshore_clearance
from app.routing.multi_service import GRAPH, calculate_multi


def roomy_vessel():
    return VesselParameters(fuel_onboard_t=9000, fuel_capacity_t=10000, displacement_ex_fuel_t=38000, reference_displacement_t=45000, engine_mcr_kw=18000)


def test_water_only_route_and_state_carry_over():
    req = MultiRouteRequest(ports=["INBOM", "LKCMB", "SGSIN"], departure_time=datetime.now(timezone.utc), vessel=roomy_vessel(), use_weather=False, use_alert_zones=False)
    result = calculate_multi(req)
    assert len(result.legs) == 2
    assert result.legs[1].summary.arrival_eta > result.legs[0].summary.arrival_eta
    assert result.legs[1].summary.fuel_remaining_t < result.legs[0].summary.fuel_remaining_t
    for leg in result.legs:
        for a, b in zip(leg.route, leg.route[1:]):
            assert edge_is_water(a, b)


def test_alert_avoidance_changes_exposure_or_distance():
    base = dict(ports=["DJJIB", "KEMBA"], vessel=roomy_vessel(), use_weather=False)
    unguarded = calculate_multi(MultiRouteRequest(**base, use_alert_zones=False))
    guarded = calculate_multi(MultiRouteRequest(**base, use_alert_zones=True, alert_avoidance=1))
    assert guarded.summary.distance_nm >= unguarded.summary.distance_nm or guarded.alert_zone_exposure != unguarded.alert_zone_exposure


def test_priority_fraction_and_percent_normalize_equally():
    assert Priorities(fuel=.5, time=.3, safety=.2).normalized() == Priorities(fuel=50, time=30, safety=20).normalized()


def test_live_forecast_does_not_clamp_out_of_range_dates():
    hourly = {"time": ["2026-08-19T00:00", "2026-08-19T01:00"], "wind_speed_10m": [5, 7]}
    with pytest.raises(ValueError, match="outside the available"):
        OpenMeteoEnvironmentProvider._nearest(hourly, "wind_speed_10m", datetime(2026, 9, 1, tzinfo=timezone.utc))


def test_mumbai_karachi_route_bends_offshore_around_gujarat():
    result = calculate_multi(MultiRouteRequest(ports=["INBOM", "PKKHI"], vessel=roomy_vessel(), use_weather=False, use_alert_zones=False))
    points = result.legs[0].route
    assert all(edge_is_water(a, b) for a, b in zip(points, points[1:]))
    offshore = [p for p in points if 20.0 <= p.lat <= 23.5]
    assert offshore and all(has_offshore_clearance(p.lat, p.lng) for p in offshore)
