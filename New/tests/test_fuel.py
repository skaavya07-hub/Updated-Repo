from app.models import VesselParameters
from app.routing.fuel import segment_performance


def test_cubic_speed_increases_fuel():
    vessel = VesselParameters()
    slow = segment_performance(100, 12, 0, 0, 0, 2000, vessel)
    fast = segment_performance(100, 16, 0, 0, 0, 2000, vessel)
    assert slow and fast
    assert fast.fuel_t > slow.fuel_t


def test_assisting_current_reduces_fuel_for_distance():
    vessel = VesselParameters()
    assisted = segment_performance(100, 14, 1, 0, 0, 2000, vessel)
    opposed = segment_performance(100, 14, -1, 0, 0, 2000, vessel)
    assert assisted.fuel_t < opposed.fuel_t


def test_ship_resistance_profile_changes_fuel_estimate():
    vessel = VesselParameters()
    container = segment_performance(100, 14, 0, 0, 0, 2000, vessel, resistance_multiplier=0.98)
    bulk_carrier = segment_performance(100, 14, 0, 0, 0, 2000, vessel, resistance_multiplier=1.08)
    assert container and bulk_carrier
    assert bulk_carrier.fuel_t > container.fuel_t
