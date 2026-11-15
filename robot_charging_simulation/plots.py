"""Polish chart labels; all displayed values come from simulation results."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments import DISTRIBUTION_LABELS
from models import SimulationResult


# PL: Kolor oznacza rozkład/model, a styl linii rozróżnia serie tego samego koloru.
SERIES_COLORS = {
    "poisson": "#1f77b4",
    "deterministic": "#ff7f0e",
    "closed": "#2ca02c",
}
LINE_STYLES = (
    "-", "--", ":", "-.",
    (0, (5, 1)), (0, (3, 1, 1, 1)), (0, (5, 1, 1, 1)),
    (0, (3, 1, 1, 1, 1, 1)), (0, (5, 2, 1, 2, 1, 2)),
    (0, (1, 3)), (0, (5, 3)), (0, (3, 2, 1, 2)),
)


def _result_color(result: SimulationResult) -> str:
    key = "closed" if result.config.model == "closed" else result.config.arrival_distribution
    return SERIES_COLORS[key]


def result_label(result: SimulationResult) -> str:
    if result.config.model == "closed":
        if result.config.individual_service:
            return f"Zamknięty · indywidualna obsługa, N={result.config.fleet_size}, c={result.config.chargers}"
        return f"Zamknięty, N={result.config.fleet_size}, c={result.config.chargers}"
    return DISTRIBUTION_LABELS[result.config.arrival_distribution]


def _format_axis(axis, title: str, y_label: str, probability: bool = False):
    axis.set_title(title, fontsize=12)
    axis.set_xlabel("Czas symulacji [min]")
    axis.set_ylabel(y_label)
    axis.grid(alpha=0.25)
    if probability:
        axis.set_ylim(0, 1.02)


def _history_panel(results, metrics, title, y_label, probability=False):
    figure, axis = plt.subplots(figsize=(8.5, 4.3), layout="constrained")
    for result in results:
        frame = pd.DataFrame(result.history)
        for index, (metric, label) in enumerate(metrics):
            axis.plot(
                frame["time"], frame[metric],
                label=f"{result_label(result)} · {label}",
                color=_result_color(result), linestyle=LINE_STYLES[index], linewidth=1.7,
            )
    _format_axis(axis, title, y_label, probability)
    # PL: Legenda jest poza obszarem danych, żeby nie zasłaniać przebiegu.
    figure.legend(*axis.get_legend_handles_labels(), loc="outside lower center", fontsize=10, ncol=2 if len(results) > 1 else 1)
    return figure


def history_charts(results: list[SimulationResult]) -> dict:
    """Plot every requested running metric and the occupancy distribution."""
    figures = {
        "mean_counts": _history_panel(
            results,
            [("mean_queue_length", "Q — kolejka"), ("mean_system_size", "K — system")],
            "Średnia liczba zgłoszeń od początku symulacji", "Liczba zgłoszeń",
        ),
        "mean_times": _history_panel(
            results,
            [("mean_wait_time", "W — kolejka")],
            "Średni czas oczekiwania w kolejce", "Czas [min]",
        ),
        "empty_queue": _history_panel(
            results, [("queue_empty_probability", "pusta kolejka")],
            "Prawdopodobieństwo pustej kolejki od początku symulacji",
            "Udział czasu", probability=True,
        ),
        "utilization": _history_panel(
            results, [("utilization", "wykorzystanie")],
            "Średnie wykorzystanie ładowarek od początku symulacji",
            "Udział dostępnego czasu ładowarek", probability=True,
        ),
    }
    for result in results:
        frame = pd.DataFrame(result.history)
        columns = [f"prob_busy_{k}" for k in range(result.config.chargers + 1)]
        figure, axis = plt.subplots(figsize=(8.5, 4.5), layout="constrained")
        if result.config.chargers <= 10:
            for count, column in enumerate(columns):
                axis.plot(
                    frame["time"], frame[column], label=f"P(B={count})",
                    color=_result_color(result), linestyle=LINE_STYLES[count],
                )
            _format_axis(axis, f"Liczba zajętych ładowarek · {result_label(result)}", "Udział czasu", True)
            figure.legend(*axis.get_legend_handles_labels(), loc="outside lower center", fontsize=10, ncol=min(4, len(columns)))
        else:
            # PL: Dla wielu ładowarek mapa pokazuje wszystkie stany bez plątaniny linii.
            image = axis.pcolormesh(
                frame["time"], np.arange(len(columns)), frame[columns].to_numpy().T,
                shading="nearest", vmin=0, vmax=1, cmap="viridis",
            )
            _format_axis(axis, f"P(B=k) w czasie · {result_label(result)}", "Zajęte ładowarki k")
            figure.colorbar(image, ax=axis, label="Udział czasu")
        figures[f"occupancy_{result.config.variant_key}"] = figure
    if results[0].config.model == "closed":
        figures["availability"] = _history_panel(
            results, [("availability", "A")],
            "Dostępność floty od początku symulacji", "Udział floty", True,
        )
    return figures


def experiment_chart(summary: pd.DataFrame, columns: int = 2):
    """Error bars show one sample SD, not confidence intervals."""
    closed = summary.iloc[0]["model"] == "closed"
    metrics = [
        ("mean_queue_length", "Średnia liczba w kolejce", "Zgłoszenia"),
        ("mean_system_size", "Średnia liczba w systemie", "Zgłoszenia"),
        ("mean_wait_time", "Średni czas w kolejce", "Minuty"),
        ("queue_empty_probability", "P(pusta kolejka)", "Prawdopodobieństwo"),
        ("utilization", "Wykorzystanie ładowarek", "Udział czasu"),
    ]
    if closed:
        metrics += [
            ("availability", "Dostępność floty A", "Udział floty"),
        ]
    rows = (len(metrics) + columns - 1) // columns
    figure, axes = plt.subplots(
        rows, columns,
        figsize=(12 if columns == 2 else 8.5, 3.5 * rows),
        layout="constrained", squeeze=False,
    )
    grouping = ["fleet_size"] if closed else ["arrival_rate_per_hour", "distribution"]
    variants = summary["fleet_size" if closed else "arrival_rate_per_hour"].drop_duplicates().tolist()
    for axis, (metric, title, unit) in zip(axes.flat, metrics):
        for group_key, group in summary.groupby(grouping, dropna=False, sort=False):
            group = group.sort_values("chargers")
            key = group_key if isinstance(group_key, tuple) else (group_key,)
            label = f"N={int(key[0])}" if closed else f"λ={key[0]:g}/h · {DISTRIBUTION_LABELS[key[1]]}"
            deviations = group[f"{metric}_std"].fillna(0).to_numpy()
            # PL: Różne wartości λ (lub N) mają różne style, ale zachowują kolor rozkładu.
            axis.errorbar(
                group["chargers"], group[metric], yerr=deviations,
                color=SERIES_COLORS["closed" if closed else key[1]],
                linestyle=LINE_STYLES[variants.index(key[0]) % len(LINE_STYLES)],
                marker="o", capsize=3, label=label,
            )
        axis.set_title(title)
        axis.set_xlabel("Liczba ładowarek c")
        axis.set_ylabel(unit)
        axis.set_xticks(sorted(summary["chargers"].unique()))
        axis.grid(alpha=0.25)
    for axis in list(axes.flat)[len(metrics):]:
        figure.delaxes(axis)
    figure.legend(*axes.flat[0].get_legend_handles_labels(), loc="outside lower center", fontsize=10, ncol=2)
    title = "Eksperymenty — średnia z powtórzeń ± jedno odchylenie standardowe"
    if summary.iloc[0].get("service_type") == "individual_deterministic":
        title = "Indywidualna obsługa · stałe czasy ładowarek\n" + title
    figure.suptitle(title, fontsize=13)
    return figure
