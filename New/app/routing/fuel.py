from dataclasses import dataclass

from app.models import VesselParameters


@dataclass
class SegmentPerformance:
    fuel_t: float
    hours: float
    speed_through_water_kn: float
    speed_over_ground_kn: float
    engine_load: float


def segment_performance(distance_nm: float, speed_kn: float, current_component_kn: float, wind_head_ms: float, wave_head_m: float, fuel_t: float, v: VesselParameters, resistance_multiplier: float = 1.0) -> SegmentPerformance | None:
    displacement = v.displacement_ex_fuel_t + fuel_t
    displacement_factor = (displacement / v.reference_displacement_t) ** (2 / 3)
    draft_factor = (v.actual_draft_m / v.design_draft_m) ** 0.35
    resistance = (1 + max(0, wind_head_ms) * 0.009 + max(0, wave_head_m) * 0.055) * resistance_multiplier
    efficiency = v.propulsion_efficiency_percent / 100
    base_load = v.normal_engine_load_percent / 100
    power_kw = v.engine_mcr_kw * base_load * (speed_kn / v.service_speed_kn) ** 3 * displacement_factor * draft_factor * resistance
    if power_kw > v.engine_mcr_kw:
        return None
    sog = max(2.0, speed_kn + current_component_kn)
    hours = distance_nm / sog
    fuel = power_kw * hours * v.sfoc_g_kwh / 1_000_000 / efficiency
    return SegmentPerformance(fuel, hours, speed_kn, sog, power_kw / v.engine_mcr_kw)
