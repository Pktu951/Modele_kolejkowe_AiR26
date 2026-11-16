"""Shared configuration and results. All simulation times are in minutes."""

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class SimulationConfig:
    model: str = "open"
    chargers: int = 2
    duration: float = 1440.0
    # PL: Dla stałej obsługi to dokładny czas, a dla wykładniczej średnia z rozkładu.
    mean_charge_time: float = 20.0
    charger_times: tuple[float, ...] | None = None
    arrival_rate: float = 4.0 / 60.0
    arrival_distribution: str = "poisson"
    service_distribution: str = "deterministic"
    fleet_size: int = 10
    mean_work_time: float = 120.0
    seed: int = 42
    sample_count: int = 301
    max_events: int = 500_000

    def __post_init__(self) -> None:
        # PL: Po odczycie JSON lista czasów też staje się niezmienną krotką.
        if isinstance(self.charger_times, list):
            object.__setattr__(self, "charger_times", tuple(self.charger_times))

    @property
    def individual_service(self) -> bool:
        return self.charger_times is not None

    @property
    def service_type(self) -> str:
        if self.individual_service:
            return "individual_deterministic"
        return f"shared_{self.service_distribution}"

    @property
    def variant_key(self) -> str:
        if self.individual_service:
            return "closed_individual"
        # PL: Zachowujemy dawne nazwy dla stałej obsługi; wykładnicza ma osobny eksport.
        name = "closed" if self.model == "closed" else self.arrival_distribution
        if self.service_distribution == "exponential":
            return f"{name}_exponential"
        return name

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
        if self.arrival_distribution != "poisson":
            raise ValueError("Only Poisson arrivals are supported in the open model.")
        if self.service_distribution not in ("deterministic", "exponential"):
            raise ValueError("Unknown service distribution.")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Seed must be a nonnegative integer.")
        if self.model == "closed":
            if self.chargers > self.fleet_size:
                raise ValueError("The closed model requires chargers <= fleet size.")
        if self.individual_service:
            if self.model != "closed":
                raise ValueError("Individual charger times require the closed model.")
            if self.service_distribution != "deterministic":
                raise ValueError("Individual charger times require deterministic service.")
            if not isinstance(self.charger_times, tuple) or len(self.charger_times) != self.chargers:
                raise ValueError("Provide exactly one fixed charging time per charger.")
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value <= 0
                for value in self.charger_times
            ):
                raise ValueError("Individual charging times must be finite and positive.")

    def to_dict(self) -> dict:
        values = asdict(self)
        if self.individual_service:
            # PL: Ten wariant używa stałych czasów, więc wspólna średnia jest zbędna.
            values.pop("mean_charge_time")
        return values


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
