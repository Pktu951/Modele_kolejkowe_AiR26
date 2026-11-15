"""Exact time integrals and running estimates, independent of plot sampling."""

from math import nan


class TimeStatistics:
    def __init__(self, chargers: int, fleet_size: int | None):
        self.chargers = chargers
        self.fleet_size = fleet_size
        self.last_time = 0.0
        self.queue_area = 0.0
        self.system_area = 0.0
        self.busy_area = 0.0
        self.empty_queue_time = 0.0
        self.occupancy_times = [0.0] * (chargers + 1)
        self.available_area = 0.0
        self.arrivals = 0
        self.service_starts = 0
        self.completions = 0
        self.wait_sum = 0.0
        self.system_time_sum = 0.0

    def advance(self, time: float, queue_length: int, busy: int) -> None:
        """Integrate the PREVIOUS state up to the next event or sample."""
        elapsed = time - self.last_time
        if elapsed < 0:
            raise ValueError("Simulation time cannot move backwards.")
        # PL: Stan jest stały pomiędzy zdarzeniami. Dodajemy pole prostokąta:
        # PL: liczba robotów razy czas, przez jaki taka liczba występowała.
        self.queue_area += queue_length * elapsed
        self.system_area += (queue_length + busy) * elapsed
        self.busy_area += busy * elapsed
        self.empty_queue_time += elapsed if queue_length == 0 else 0.0
        self.occupancy_times[busy] += elapsed
        if self.fleet_size is not None:
            available = self.fleet_size - queue_length - busy
            self.available_area += available * elapsed
        self.last_time = time

    def record_start(self, wait_time: float) -> None:
        # PL: Pełny czas oczekiwania znamy dopiero, gdy robot dostanie ładowarkę.
        self.service_starts += 1
        self.wait_sum += wait_time

    def record_completion(self, system_time: float) -> None:
        # PL: Czas w systemie obejmuje zarówno czekanie, jak i ładowanie.
        self.completions += 1
        self.system_time_sum += system_time

    def snapshot(self, time: float, queue_length: int, busy: int) -> dict:
        def time_mean(total: float) -> float:
            return total / time if time > 0 else nan

        row = {
            "time": time,
            "queue_length": queue_length,
            "system_size": queue_length + busy,
            "busy_chargers": busy,
            "mean_queue_length": time_mean(self.queue_area),
            "mean_system_size": time_mean(self.system_area),
            "mean_wait_time": (
                self.wait_sum / self.service_starts if self.service_starts else nan
            ),
            "mean_system_time": (
                self.system_time_sum / self.completions if self.completions else nan
            ),
            "queue_empty_probability": time_mean(self.empty_queue_time),
            "utilization": time_mean(self.busy_area) / self.chargers,
            "arrivals": self.arrivals,
            "service_starts": self.service_starts,
            "completions": self.completions,
            "unfinished_visits": queue_length + busy,
            "mean_available_robots": nan,
            "availability": nan,
        }
        for count, total in enumerate(self.occupancy_times):
            row[f"prob_busy_{count}"] = time_mean(total)
        if self.fleet_size is not None:
            row["mean_available_robots"] = time_mean(self.available_area)
            row["availability"] = row["mean_available_robots"] / self.fleet_size
        return row
