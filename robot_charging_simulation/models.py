"""Shared configuration and results. All simulation times are in minutes."""

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class SimulationConfig:
    model: str = "open"
    chargers: int = 2
    duration: float = 1440.0
    mean_charge_time: float = 20.0
    arrival_rate: float = 4.0 / 60.0
    arrival_distribution: str = "poisson"
    fleet_size: int = 10
    mean_work_time: float = 120.0
    min_available: int = 7
    seed: int = 42
    sample_count: int = 301
    max_events: int = 500_000

    def validate(self) -> None:
        """Reject invalid parameters before creating events."""
        if self.model not in ("open", "closed"):
            raise ValueError("Model must be 'open' or 'closed'.")
        for name in ("chargers", "fleet_size", "sample_count", "max_events"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if self.sample_count < 2:
            raise ValueError("At least two sample points are required.")
        for name in ("duration", "mean_charge_time", "arrival_rate", "mean_work_time"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.arrival_distribution not in ("poisson", "deterministic"):
            raise ValueError("Unknown arrival distribution.")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Seed must be a nonnegative integer.")
        if not isinstance(self.min_available, int) or self.min_available < 0:
            raise ValueError("Minimum available fleet must be a nonnegative integer.")
        if self.model == "closed":
            if self.chargers > self.fleet_size:
                raise ValueError("The closed model requires chargers <= fleet size.")
            if self.min_available > self.fleet_size:
                raise ValueError("Minimum available fleet cannot exceed fleet size.")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Visit:
    """One charging request; a closed-model robot can create many visits."""

    visit_id: int
    robot_id: int
    arrived_at: float
    started_at: float | None = None
    departed_at: float | None = None
    charger_id: int | None = None

    def to_dict(self) -> dict:
        row = asdict(self)
        row["wait_time"] = (
            None if self.started_at is None else self.started_at - self.arrived_at
        )
        row["system_time"] = (
            None if self.departed_at is None else self.departed_at - self.arrived_at
        )
        return row


@dataclass
class SimulationResult:
    config: SimulationConfig
    history: list[dict]
    visits: list[Visit]
    event_log: list[dict]

    @property
    def summary(self) -> dict:
        return self.history[-1]
