"""Repeat scenarios and summarize variability between independent runs."""

from dataclasses import replace
import json
from math import isfinite
from typing import Callable

import pandas as pd

from models import SimulationConfig
from simulation import simulate


METRIC_LABELS = {
    "mean_queue_length": "Średnia liczba w kolejce Q",
    "mean_system_size": "Średnia liczba w systemie K",
    "mean_wait_time": "Średni czas w kolejce W [min]",
    "mean_system_time": "Średni czas w systemie T [min]",
    "queue_empty_probability": "P(pusta kolejka)",
    "utilization": "Wykorzystanie ładowarek",
    "mean_available_robots": "Średnia liczba dostępnych E[R]",
    "availability": "Dostępność floty A",
}
DISTRIBUTION_LABELS = {
    "poisson": "Poisson (M/M/c)",
    "deterministic": "Deterministyczny (D/M/c)",
}
SERVICE_LABELS = {
    "shared_exponential": "Jednakowe ładowarki · czasy wykładnicze",
    "individual_deterministic": "Indywidualne ładowarki · stałe czasy",
}


def parse_charger_times(text: str) -> tuple[float, ...]:
    """Keep charger order and repeated values when parsing fixed durations."""
    try:
        values = tuple(float(part.strip()) for part in text.replace(";", ",").split(","))
    except ValueError as error:
        raise ValueError("Wpisz czasy ładowarek oddzielone przecinkami, np. 10, 30, 20.") from error
    if not values or any(not isfinite(value) or value <= 0 for value in values):
        raise ValueError("Czasy ładowarek muszą być skończone i większe od zera.")
    if len(values) > 64:
        raise ValueError("Można podać czasy najwyżej 64 ładowarek.")
    return values


def parse_values(text: str, integer: bool = False) -> list:
    """Parse a comma/semicolon-separated positive grid without evaluating code."""
    try:
        values = list(dict.fromkeys(float(part.strip()) for part in text.replace(";", ",").split(",")))
    except ValueError as error:
        raise ValueError("Wpisz liczby oddzielone przecinkami, np. 1, 2, 3.") from error
    if not values or any(not isfinite(value) or value <= 0 for value in values):
        raise ValueError("Wartości muszą być skończone i większe od zera.")
    if len(values) > 12:
        raise ValueError("W jednym polu można podać najwyżej 12 wartości.")
    if integer:
        if any(not value.is_integer() for value in values):
            raise ValueError("Liczby robotów i ładowarek muszą być całkowite.")
        return [int(value) for value in values]
    return values


def build_scenarios(
    base: SimulationConfig,
    charger_counts: list[int],
    fleet_sizes: list[int] | None = None,
    arrival_rates_per_hour: list[float] | None = None,
    distributions: list[str] | None = None,
    charger_times: tuple[float, ...] | None = None,
) -> tuple[list[SimulationConfig], list[str]]:
    scenarios = []
    skipped = []
    time_pool = charger_times if charger_times is not None else base.charger_times
    if charger_times is not None and not base.individual_service:
        raise ValueError("Lista czasów dotyczy modelu zamkniętego z indywidualną obsługą.")
    if base.model == "closed":
        for fleet_size in fleet_sizes or [base.fleet_size]:
            for chargers in charger_counts:
                if chargers > fleet_size:
                    skipped.append(f"N={fleet_size}, c={chargers}")
                    continue
                times = None
                if base.individual_service:
                    if len(time_pool) < chargers:
                        raise ValueError(f"Podaj co najmniej {chargers} czasów ładowarek dla wariantu c={chargers}.")
                    # PL: Zachowujemy kolejność użytkownika: c ładowarek = pierwsze c czasów.
                    times = tuple(time_pool[:chargers])
                scenarios.append(replace(base, chargers=chargers, fleet_size=fleet_size, charger_times=times))
    else:
        for rate in arrival_rates_per_hour or [base.arrival_rate * 60]:
            for chargers in charger_counts:
                for distribution in distributions or ["poisson", "deterministic"]:
                    scenarios.append(replace(
                        base, chargers=chargers, arrival_rate=rate / 60,
                        arrival_distribution=distribution,
                    ))
    for config in scenarios:
        config.validate()
    if not scenarios:
        raise ValueError("Brak poprawnych wariantów. W modelu zamkniętym wymagane c ≤ N.")
    return scenarios, skipped


def run_experiments(
    scenarios: list[SimulationConfig],
    repetitions: int,
    progress: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    if repetitions < 1:
        raise ValueError("At least one repetition is required.")
    if len(scenarios) * repetitions > 600:
        raise ValueError("Jedna seria może obejmować najwyżej 600 uruchomień.")
    rows = []
    total = len(scenarios) * repetitions
    for scenario_id, scenario in enumerate(scenarios):
        for repetition in range(repetitions):
            # PL: Ziarno zmienia się między powtórzeniami. Te same ziarna dla
            # PL: wariantów pozwalają porównywać napływy przy tych samych ładowaniach.
            config = replace(scenario, seed=scenario.seed + repetition, sample_count=2)
            result = simulate(config)
            row = dict(result.summary)
            row.update({
                "scenario_id": scenario_id,
                "repetition": repetition + 1,
                "seed": config.seed,
                "model": config.model,
                "distribution": config.arrival_distribution if config.model == "open" else "closed",
                "chargers": config.chargers,
                "fleet_size": config.fleet_size if config.model == "closed" else None,
                "arrival_rate_per_hour": config.arrival_rate * 60 if config.model == "open" else None,
                "duration": config.duration,
                "mean_charge_time": None if config.individual_service else config.mean_charge_time,
                "service_type": config.service_type,
                "charger_times": json.dumps(config.charger_times) if config.individual_service else None,
                "mean_work_time": config.mean_work_time if config.model == "closed" else None,
                "offered_utilization": (
                    config.arrival_rate * config.mean_charge_time / config.chargers
                    if config.model == "open" else None
                ),
            })
            rows.append(row)
            if progress:
                progress(len(rows), total)
    return pd.DataFrame(rows)


def summarize_experiments(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep the SD of repetitions separate from the mean of repetitions."""
    rows = []
    metadata = [
        "scenario_id", "model", "distribution", "chargers", "fleet_size",
        "arrival_rate_per_hour", "duration", "mean_charge_time", "mean_work_time",
        "offered_utilization", "service_type", "charger_times",
    ]
    for _, group in raw.groupby("scenario_id", sort=False):
        row = {name: group.iloc[0][name] for name in metadata}
        row["repetitions"] = len(group)
        for name in METRIC_LABELS:
            values = group[name].dropna()
            row[name] = values.mean()
            row[f"{name}_std"] = values.std(ddof=1)
            row[f"{name}_observed_runs"] = len(values)
        for column in raw.columns:
            if column.startswith("prob_busy_"):
                row[column] = group[column].mean()
        rows.append(row)
    return pd.DataFrame(rows)
