"""Reproduce report tables, plots and CSV data using the actual project engine."""

from dataclasses import replace
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent / "robot_charging_simulation"
sys.path.insert(0, str(PROJECT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

from experiments import build_scenarios, queue_model_name, run_experiments, summarize_experiments
from metrics import closed_arrival_summary, instantaneous_history
from models import SimulationConfig
from simulation import simulate


def number(value, digits=3):
    return f"{value:.{digits}f}".replace(".", ",")


def write_table(name, columns, header, rows):
    content = [r"\begin{tabular}{" + columns + "}", r"\toprule", header + r" \\", r"\midrule"]
    content.extend(" & ".join(row) + r" \\" for row in rows)
    content.extend([r"\bottomrule", r"\end{tabular}"])
    (ROOT / "tables" / f"{name}.tex").write_text("\n".join(content) + "\n")
    # PL: Tabele wstawiamy też bezpośrednio do main.tex, aby można było wkleić jeden plik.
    source = ROOT / "main.tex"
    if source.exists():
        text = source.read_text()
        start, end = f"% BEGIN GENERATED TABLE: {name}", f"% END GENERATED TABLE: {name}"
        block = start + "\n" + "\n".join(content) + "\n" + end
        if start in text:
            text = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, text, flags=re.S)
        else:
            text = text.replace(r"\input{tables/" + name + ".tex}", block)
        source.write_text(text)


def run_series(name, scenarios):
    raw = run_experiments(scenarios, 5)
    summary = summarize_experiments(raw)
    raw.to_csv(ROOT / "data" / f"{name}_runs.csv", index=False)
    summary.to_csv(ROOT / "data" / f"{name}_summary.csv", index=False)
    (ROOT / "data" / f"{name}_scenarios.json").write_text(
        json.dumps([s.to_dict() for s in scenarios], indent=2), encoding="utf-8"
    )
    return summary


def main():
    for folder in ("figures", "tables", "data"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    base = SimulationConfig(duration=168 * 60, seed=42, mean_charge_time=20, mean_work_time=120)
    open_cases, closed_cases = [], []
    for service in ("deterministic", "exponential"):
        config = replace(base, service_distribution=service)
        open_cases.extend(build_scenarios(config, [1, 2, 3], arrival_rates_per_hour=[4])[0])
        closed_cases.extend(build_scenarios(replace(config, model="closed"), [1, 2, 3], fleet_sizes=[10, 15, 20])[0])
    opened = run_series("open", open_cases)
    closed = run_series("closed", closed_cases)
    profiles = [
        replace(base, model="closed", chargers=2, fleet_size=10),
        replace(base, model="closed", chargers=2, fleet_size=10, charger_times=(20., 20.)),
        replace(base, model="closed", chargers=2, fleet_size=10, charger_times=(15., 30.)),
        replace(base, model="closed", chargers=2, fleet_size=10, charger_times=(10., 30.)),
    ]
    individual = run_series("individual", profiles)
    open_rows = []
    for _, row in opened.sort_values(["chargers", "service_distribution"]).iterrows():
        label = queue_model_name(row.service_distribution)
        wait = r"\(" + number(row.mean_wait_time) + r" \pm " + number(row.mean_wait_time_std) + r"\)"
        open_rows.append([label, str(int(row.chargers)), number(row.offered_utilization, 2), number(row.mean_queue_length), wait, number(100 * row.utilization, 1)])
    write_table("open", "lrrrrr", r"Model & $c$ & $\rho$ & $Q$ & $W\pm s_W$ [min] & $u$ [\%]", open_rows)
    closed_rows = []
    for _, row in closed[closed.fleet_size.eq(10)].sort_values(["chargers", "service_distribution"]).iterrows():
        closed_rows.append([queue_model_name(row.service_distribution), str(int(row.chargers)), number(row.mean_queue_length), number(row.mean_wait_time), number(row.mean_available_robots), number(100 * row.utilization, 1), number(100 * row.availability, 1)])
    write_table("closed", "lrrrrrr", r"Model & $c$ & $Q$ & $W$ [min] & $E[R]$ & $u$ [\%] & $A$ [\%]", closed_rows)
    individual_rows = []
    labels = ["Wspólna stała", "Indywidualna", "Indywidualna", "Indywidualna"]
    for index, (_, row) in enumerate(individual.iterrows()):
        times = profiles[index].charger_times or (20., 20.)
        capacity = sum(60 / value for value in times)
        individual_rows.append([labels[index], "; ".join(number(t, 0) for t in times), number(capacity, 1), number(row.mean_wait_time), number(100 * row.availability, 1)])
    write_table("individual", "llrrr", r"Obsługa & $d_1;d_2$ [min] & Wydajność [roboty/h] & $W$ [min] & $A$ [\%]", individual_rows)

    figure, axes = plt.subplots(1, 2, figsize=(9, 3.1), layout="constrained")
    for service, color in (("deterministic", "#27813c"), ("exponential", "#1f77b4")):
        for fleet, style in zip((10, 15, 20), ("-", "--", ":")):
            rows = closed[closed.fleet_size.eq(fleet) & closed.service_distribution.eq(service)].sort_values("chargers")
            for axis, metric, factor in ((axes[0], "mean_wait_time", 1), (axes[1], "availability", 100)):
                axis.errorbar(rows.chargers, rows[metric] * factor, yerr=rows[f"{metric}_std"] * factor,
                              label=f"{queue_model_name(service)}, N={fleet}", color=color, linestyle=style, marker="o", capsize=3)
                axis.set_xlabel("Liczba ładowarek c")
                axis.set_xticks([1, 2, 3])
                axis.grid(alpha=.22)
    axes[0].set_ylabel("Średni czas w kolejce W [min]")
    axes[1].set_ylabel("Dostępność floty A [%]")
    figure.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=3, frameon=False, fontsize=10.5)
    figure.savefig(ROOT / "figures" / "closed_experiment.png", dpi=250)
    plt.close(figure)

    result = simulate(SimulationConfig(model="closed", service_distribution="deterministic", duration=100, seed=41))
    state = closed_arrival_summary(result)
    (ROOT / "data" / "snapshot_seed41.json").write_text(
        json.dumps({"config": result.config.to_dict(), "summary": result.summary, "rates": state}, indent=2), encoding="utf-8"
    )
    trace = instantaneous_history(result)
    figure, axis = plt.subplots(figsize=(9, 2.8), layout="constrained")
    for key, label, color in (("queue_length", "Oczekujące", "#1f77b4"), ("busy_chargers", "Ładowane", "#ff7f0e")):
        axis.step([r["time"] for r in trace], [r[key] for r in trace], where="post", label=label, color=color)
    axis.set(xlim=(0, 100), ylim=(-.1, 3.4), xlabel="Czas symulacji [min]", ylabel="Liczba robotów")
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))
    axis.legend(loc="upper right", frameon=False)
    axis.grid(alpha=.22)
    figure.savefig(ROOT / "figures" / "closed_trace.png", dpi=250)
    plt.close(figure)
    # PL: Zrzut UI wykonujemy osobno w przeglądarce; skrypt nie zastępuje go starym obrazem.
    assert state["arrivals"] == 11 and state["queue_length"] == 1 and state["busy_chargers"] == 2
    assert np.isclose(individual.iloc[0].mean_wait_time, individual.iloc[1].mean_wait_time)
    print("Saved 140 real simulation runs, three tables and two plots; preserved the UI screenshot and logo.")


if __name__ == "__main__":
    main()
