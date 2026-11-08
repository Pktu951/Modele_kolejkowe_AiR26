"""FIFO charging simulation using a discrete-event calendar, not real-time sleeps."""

from collections import deque
from heapq import heappop, heappush
from random import Random

from metrics import TimeStatistics
from models import SimulationConfig, SimulationResult, Visit


class SimulationLimitError(RuntimeError):
    """The requested run needs more events than the configured resource limit."""


class ChargingSimulation:
    """A robot works outside the station, queues, charges, and optionally returns."""

    def __init__(self, config: SimulationConfig):
        config.validate()
        self.config = config
        # PL: Oddzielne generatory oddzielają losowanie napływu, ładowania i pracy.
        # PL: Dla tego samego ziarna porównanie napływów używa tych samych ładowań.
        seeds = Random(config.seed)
        self.arrival_rng = Random(seeds.getrandbits(64))
        self.charge_rng = Random(seeds.getrandbits(64))
        self.work_rng = Random(seeds.getrandbits(64))
        self.events: list[tuple] = []
        self.sequence = 0
        self.queue: deque[Visit] = deque()
        self.slots: list[Visit | None] = [None] * config.chargers
        self.busy = 0
        self.visits: list[Visit] = []
        self.history: list[dict] = []
        self.event_log: list[dict] = []
        self.statistics = TimeStatistics(
            config.chargers,
            config.fleet_size if config.model == "closed" else None,
            config.min_available,
        )

    def arrival_interval(self) -> float:
        """Poisson arrivals have exponential interarrival times."""
        if self.config.arrival_distribution == "poisson":
            # PL: Losujemy odstęp między zgłoszeniami, a nie liczbę minut z Poissona.
            return self.arrival_rng.expovariate(self.config.arrival_rate)
        # PL: Rozkład deterministyczny D: odstęp zawsze równy 1 / lambda.
        return 1.0 / self.config.arrival_rate

    def charge_duration(self) -> float:
        return self.charge_rng.expovariate(1.0 / self.config.mean_charge_time)

    def work_duration(self) -> float:
        return self.work_rng.expovariate(1.0 / self.config.mean_work_time)

    def schedule(self, time: float, kind: str, robot_id: int = -1, charger_id: int = -1):
        if time > self.config.duration:
            return
        # PL: Przy remisie najpierw kończymy ładowanie, potem obsługujemy napływ,
        # PL: a dopiero na końcu zapisujemy punkt wykresu.
        priority = {"departure": 0, "arrival": 1, "sample": 2}[kind]
        self.sequence += 1
        heappush(self.events, (time, priority, self.sequence, kind, robot_id, charger_id))

    def start_charge(self, visit: Visit, charger_id: int, time: float) -> None:
        visit.started_at = time
        visit.charger_id = charger_id
        self.slots[charger_id] = visit
        self.busy += 1
        self.statistics.record_start(time - visit.arrived_at)
        self.schedule(time + self.charge_duration(), "departure", visit.robot_id, charger_id)

    def handle_arrival(self, time: float, robot_id: int) -> None:
        self.statistics.arrivals += 1
        visit = Visit(len(self.visits), robot_id, time)
        self.visits.append(visit)
        if self.busy < self.config.chargers:
            self.start_charge(visit, self.slots.index(None), time)
        else:
            self.queue.append(visit)
        if self.config.model == "open":
            # PL: W modelu otwartym nowe zgłoszenia nie zależą od zajętości stacji.
            self.schedule(time + self.arrival_interval(), "arrival", robot_id + 1)

    def handle_departure(self, time: float, charger_id: int) -> None:
        visit = self.slots[charger_id]
        if visit is None:
            raise RuntimeError("A free charger cannot finish service.")
        visit.departed_at = time
        self.statistics.record_completion(time - visit.arrived_at)
        self.slots[charger_id] = None
        self.busy -= 1
        if self.config.model == "closed":
            # PL: Ten sam robot wraca do pracy i dopiero po niej ponownie się zgłosi.
            self.schedule(time + self.work_duration(), "arrival", visit.robot_id)
        if self.queue:
            # PL: popleft wybiera robota czekającego najdłużej (FIFO).
            self.start_charge(self.queue.popleft(), charger_id, time)

    def run(self) -> SimulationResult:
        # PL: Krok 1. Stacja jest pusta. W modelu zamkniętym wszystkie roboty pracują.
        if self.config.model == "open":
            self.schedule(self.arrival_interval(), "arrival", 0)
        else:
            for robot_id in range(self.config.fleet_size):
                self.schedule(self.work_duration(), "arrival", robot_id)
        for index in range(self.config.sample_count):
            self.schedule(
                self.config.duration if index == self.config.sample_count - 1
                else self.config.duration * index / (self.config.sample_count - 1), "sample"
            )

        event_count = 0
        while self.events:
            time, _, _, kind, robot_id, charger_id = heappop(self.events)
            # PL: Krok 2. Najpierw doliczamy czas spędzony w dotychczasowym stanie.
            self.statistics.advance(time, len(self.queue), self.busy)
            # PL: Krok 3. Zdarzenie zmienia stan; próbka jedynie odczytuje wyniki.
            if kind == "sample":
                self.history.append(self.statistics.snapshot(time, len(self.queue), self.busy))
                continue
            event_count += 1
            if event_count > self.config.max_events:
                raise SimulationLimitError(
                    "Event limit exceeded. Shorten the duration or reduce the arrival rate."
                )
            if kind == "arrival":
                self.handle_arrival(time, robot_id)
            else:
                self.handle_departure(time, charger_id)
            if len(self.event_log) < 500:
                self.event_log.append({
                    "time": time, "event": kind, "robot_id": robot_id,
                    "charger_id": charger_id if kind == "departure" else None,
                    "queue_length": len(self.queue), "busy_chargers": self.busy,
                    "working_robots": (
                        self.config.fleet_size - len(self.queue) - self.busy
                        if self.config.model == "closed" else None
                    ),
                })
        # PL: Krok 4. Kończymy dokładnie w zadanym czasie, bez opróżniania kolejki.
        return SimulationResult(self.config, self.history, self.visits, self.event_log)


def simulate(config: SimulationConfig) -> SimulationResult:
    return ChargingSimulation(config).run()
