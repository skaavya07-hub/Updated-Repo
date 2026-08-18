from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Priorities(BaseModel):
    fuel: float = 50
    time: float = 30
    safety: float = 20

    @field_validator("fuel", "time", "safety", mode="before")
    @classmethod
    def accept_fraction_or_percent(cls, value):
        value = float(value)
        if value < 0:
            raise ValueError("Priorities cannot be negative")
        return value * 100 if value <= 1 else value

    def normalized(self) -> tuple[float, float, float]:
        total = self.fuel + self.time + self.safety
        if total <= 0:
            raise ValueError("At least one optimization priority must be positive")
        return self.fuel / total, self.time / total, self.safety / total


class VesselParameters(BaseModel):
    fuel_onboard_t: float = Field(2500, gt=0)
    fuel_capacity_t: float = Field(3200, gt=0)
    fuel_reserve_percent: float = Field(15, ge=0, lt=100)
    displacement_ex_fuel_t: float = Field(38000, gt=0)
    reference_displacement_t: float = Field(40000, gt=0)
    actual_draft_m: float = Field(10.5, gt=0)
    design_draft_m: float = Field(12, gt=0)
    service_speed_kn: float = Field(16, ge=5, le=35)
    engine_mcr_kw: float = Field(12000, gt=0)
    normal_engine_load_percent: float = Field(75, gt=0, le=100)
    sfoc_g_kwh: float = Field(175, ge=80, le=400)
    propulsion_efficiency_percent: float = Field(70, gt=0, le=100)
    max_wave_height_m: float = Field(6, gt=0, le=20)
    max_wind_speed_ms: float = Field(25, gt=0, le=80)

    @model_validator(mode="after")
    def validate_relationships(self):
        if self.fuel_onboard_t > self.fuel_capacity_t:
            raise ValueError("Fuel onboard cannot exceed tank capacity")
        if self.actual_draft_m > self.design_draft_m * 1.08:
            raise ValueError("Actual draft exceeds the permitted design limit")
        return self


class RouteRequest(BaseModel):
    origin: str
    destination: str
    departure_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vessel: VesselParameters = Field(default_factory=VesselParameters)
    priorities: Priorities = Field(default_factory=Priorities)
    use_weather: bool = True
    use_alert_zones: bool = True
    alert_avoidance: float = Field(0.8, ge=0, le=1)


class MultiRouteRequest(BaseModel):
    ports: list[str] = Field(min_length=2, max_length=8)
    departure_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vessel: VesselParameters = Field(default_factory=VesselParameters)
    priorities: Priorities = Field(default_factory=Priorities)
    use_weather: bool = True
    use_alert_zones: bool = True
    alert_avoidance: float = Field(0.8, ge=0, le=1)

    @field_validator("ports")
    @classmethod
    def no_consecutive_duplicates(cls, ports):
        if any(a == b for a, b in zip(ports, ports[1:])):
            raise ValueError("Consecutive voyage ports must be different")
        return ports


class Point(BaseModel):
    lat: float
    lng: float


class LegSummary(BaseModel):
    origin: str
    destination: str
    distance_nm: float
    fuel_consumed_t: float
    voyage_hours: float
    average_speed_kn: float
    safety_score: float
    fuel_remaining_t: float
    arrival_eta: datetime


class LegResult(BaseModel):
    origin: str
    destination: str
    color: str
    route: list[Point]
    summary: LegSummary


class TotalSummary(BaseModel):
    distance_nm: float
    voyage_hours: float
    fuel_consumed_t: float
    fuel_remaining_t: float
    average_speed_kn: float
    co2_emissions_t: float
    safety_score: float
    max_wave_height_m: float
    max_wind_speed_ms: float
    arrival_eta: datetime
    cells_evaluated: int
    computation_ms: float
    voyage_legs: int
    route_points: int


class RouteResponse(BaseModel):
    combined_route: list[Point]
    legs: list[LegResult]
    summary: TotalSummary
    warnings: list[str]
    environmental_source: str
    alert_zone_exposure: list[str]

